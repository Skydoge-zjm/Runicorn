from __future__ import annotations

import os
import threading
import time
import traceback
import posixpath
from pathlib import Path
from io import StringIO
import stat as statmod
from typing import Dict, List, Optional, Tuple

import paramiko


class SSHSession:
    def __init__(self, host: str, port: int, username: str,
                 password: Optional[str] = None,
                 pkey_str: Optional[str] = None,
                 pkey_path: Optional[str] = None,
                 passphrase: Optional[str] = None,
                 use_agent: bool = True,
                 timeout: float = 15.0):
        self.host = host
        self.port = int(port or 22)
        self.username = username
        self.password = password
        self.pkey_str = pkey_str
        self.pkey_path = pkey_path
        self.passphrase = passphrase
        self.use_agent = use_agent
        self.timeout = timeout
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None
        self.id = f"{self.username}@{self.host}:{self.port}:{int(time.time()*1000)}"

    def connect(self):
        if self.client:
            return
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs = {
            "hostname": self.host,
            "port": self.port,
            "username": self.username,
            "timeout": self.timeout,
            "allow_agent": bool(self.use_agent),
            "look_for_keys": bool(self.use_agent),
        }
        if self.password:
            kwargs["password"] = self.password
        pkey = None
        if self.pkey_str:
            try:
                pkey = paramiko.RSAKey.from_private_key(file_obj=StringIO(self.pkey_str), password=self.passphrase)
            except Exception:
                try:
                    pkey = paramiko.Ed25519Key.from_private_key(file_obj=StringIO(self.pkey_str), password=self.passphrase)
                except Exception:
                    pass
        elif self.pkey_path:
            p = Path(self.pkey_path).expanduser()
            if p.exists():
                try:
                    pkey = paramiko.RSAKey.from_private_key_file(str(p), password=self.passphrase)
                except Exception:
                    try:
                        pkey = paramiko.Ed25519Key.from_private_key_file(str(p), password=self.passphrase)
                    except Exception:
                        pass
        if pkey is not None:
            kwargs["pkey"] = pkey

        client.connect(**kwargs)
        self.client = client
        self.sftp = client.open_sftp()

    def close(self):
        try:
            if self.sftp:
                self.sftp.close()
        finally:
            self.sftp = None
        try:
            if self.client:
                self.client.close()
        finally:
            self.client = None


class MirrorTask:
    def __init__(self, session: SSHSession, remote_root: str, local_root: Path, interval: float = 2.0):
        self.session = session
        self.remote_root = remote_root.rstrip('/')
        self.local_root = Path(local_root)
        self.interval = max(0.5, interval)
        self.id = f"mirror:{self.session.id}:{int(time.time()*1000)}"
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.stats = {
            "copied_files": 0,
            "appended_bytes": 0,
            "scans": 0,
            "started_at": time.time(),
            "last_error": "",
        }
        # map of remote posix path -> last size
        self._known_sizes: Dict[str, int] = {}

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=3.0)

    def _ensure_local_parent(self, rel: str) -> Path:
        p = self.local_root / Path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _walk(self, sftp: paramiko.SFTPClient, path: str) -> List[Tuple[str, List[paramiko.SFTPAttributes], List[paramiko.SFTPAttributes]]]:
        """like os.walk for SFTP: returns (dirpath, dirs, files) with posix paths"""
        out = []
        try:
            entries = sftp.listdir_attr(path)
        except IOError:
            return out
        dirs = []
        files = []
        for e in entries:
            name = e.filename
            if name in (".", ".."):
                continue
            full = posixpath.join(path, name)
            if statmod.S_ISDIR(e.st_mode):
                dirs.append((full, e))
            else:
                files.append((full, e))
        out.append((path, [d[1] for d in dirs], [f[1] for f in files]))
        for dfull, dattr in dirs:
            out.extend(self._walk(sftp, dfull))
        return out

    def _copy_file_full(self, sftp: paramiko.SFTPClient, rpath: str, lpath: Path):
        with sftp.open(rpath, 'rb') as rf, open(lpath, 'wb') as lf:
            while True:
                data = rf.read(1024 * 1024)
                if not data:
                    break
                lf.write(data)
        self.stats["copied_files"] += 1

    def _append_new_bytes(self, sftp: paramiko.SFTPClient, rpath: str, lpath: Path, from_size: int):
        with sftp.open(rpath, 'rb') as rf:
            rf.seek(from_size)
            with open(lpath, 'ab') as lf:
                while True:
                    data = rf.read(1024 * 64)
                    if not data:
                        break
                    lf.write(data)
                    self.stats["appended_bytes"] += len(data)

    def _run(self):
        while not self._stop.is_set():
            try:
                if not self.session.sftp:
                    # try reconnect once
                    self.session.connect()
                sftp = self.session.sftp
                if not sftp:
                    time.sleep(self.interval)
                    continue
                self.stats["scans"] += 1
                # Walk remote
                for dirpath, _dirs, _files in [(self.remote_root, None, None)]:
                    # single-level bootstrap to avoid deep recursion issues on very large trees
                    pass
                # Use custom walk
                for (dpath, _dirs, files) in self._walk(sftp, self.remote_root):
                    for fattr in files:
                        rpath = posixpath.join(dpath, fattr.filename)
                        try:
                            rel = posixpath.relpath(rpath, start=self.remote_root)
                        except Exception:
                            # if rel fails, skip
                            continue
                        # map to local
                        lpath = self._ensure_local_parent(rel)
                        rsize = int(getattr(fattr, 'st_size', 0) or 0)
                        last = self._known_sizes.get(rpath)
                        # Special handling for append-only files
                        base = fattr.filename.lower()
                        if last is None:
                            # new file: copy full
                            self._copy_file_full(sftp, rpath, lpath)
                            self._known_sizes[rpath] = rsize
                        else:
                            if rsize > last:
                                # append new bytes
                                self._append_new_bytes(sftp, rpath, lpath, from_size=last)
                                self._known_sizes[rpath] = rsize
                            elif rsize < last:
                                # file truncated/rotated: recopy full
                                self._copy_file_full(sftp, rpath, lpath)
                                self._known_sizes[rpath] = rsize
                # Sleep
                time.sleep(self.interval)
            except Exception as e:
                self.stats["last_error"] = f"{e}\n{traceback.format_exc()}"
                # brief backoff
                time.sleep(self.interval)


_SESSIONS: Dict[str, SSHSession] = {}
_MIRRORS: Dict[str, MirrorTask] = {}
_LOCK = threading.Lock()


def create_session(**kwargs) -> SSHSession:
    sess = SSHSession(**kwargs)
    sess.connect()
    with _LOCK:
        _SESSIONS[sess.id] = sess
    return sess


def get_session(session_id: str) -> Optional[SSHSession]:
    with _LOCK:
        return _SESSIONS.get(session_id)


def close_session(session_id: str) -> bool:
    with _LOCK:
        sess = _SESSIONS.pop(session_id, None)
    if not sess:
        return False
    try:
        sess.close()
    except Exception:
        pass
    return True


def list_sessions() -> List[dict]:
    out = []
    with _LOCK:
        for sid, s in _SESSIONS.items():
            out.append({
                "id": sid,
                "host": s.host,
                "port": s.port,
                "username": s.username,
            })
    return out


def sftp_listdir(session_id: str, path: str) -> List[dict]:
    sess = get_session(session_id)
    if not sess or not sess.sftp:
        raise RuntimeError("session not connected")
    sftp = sess.sftp
    # Default path
    if not path:
        path = '.'
    try:
        entries = sftp.listdir_attr(path)
    except IOError:
        # try expand ~
        if path.startswith('~'):
            try:
                stdin, stdout, stderr = sess.client.exec_command('echo -n $HOME')  # type: ignore
                home = stdout.read().decode('utf-8')
                if home:
                    path = path.replace('~', home, 1)
                    entries = sftp.listdir_attr(path)
                else:
                    entries = []
            except Exception:
                entries = []
        else:
            entries = []
    out: List[dict] = []
    for e in entries:
        name = e.filename
        full = posixpath.join(path, name)
        typ = 'dir' if statmod.S_ISDIR(e.st_mode) else 'file'
        out.append({
            'name': name,
            'path': full,
            'type': typ,
            'size': int(getattr(e, 'st_size', 0) or 0),
            'mtime': int(getattr(e, 'st_mtime', 0) or 0),
        })
    # Sort: dirs first, then files
    out.sort(key=lambda x: (x['type'] != 'dir', x['name'].lower()))
    return out


def start_mirror(session_id: str, remote_root: str, local_root: Path, interval: float = 2.0) -> MirrorTask:
    sess = get_session(session_id)
    if not sess:
        raise RuntimeError("session not found")
    task = MirrorTask(sess, remote_root=remote_root, local_root=local_root, interval=interval)
    with _LOCK:
        _MIRRORS[task.id] = task
    task.start()
    return task


def stop_mirror(task_id: str) -> bool:
    with _LOCK:
        task = _MIRRORS.pop(task_id, None)
    if not task:
        return False
    try:
        task.stop()
    except Exception:
        pass
    return True


def list_mirrors() -> List[dict]:
    out = []
    with _LOCK:
        items = list(_MIRRORS.items())
    for tid, t in items:
        out.append({
            'id': tid,
            'session_id': t.session.id,
            'host': t.session.host,
            'remote_root': t.remote_root,
            'local_root': str(t.local_root),
            'interval': t.interval,
            'stats': dict(t.stats),
            'alive': t._thread.is_alive(),
        })
    return out
