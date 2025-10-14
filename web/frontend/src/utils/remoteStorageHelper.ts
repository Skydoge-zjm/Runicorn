/**
 * Remote Storage Helper Utilities
 * 
 * Provides helper functions for remote storage operations in UI components.
 */

import { message } from 'antd'
import { 
  getStorageMode, 
  remoteDownloadArtifact, 
  getDownloadStatus,
  cancelDownload 
} from '../api'

/**
 * Check if currently in remote storage mode
 */
export async function checkIsRemoteMode(): Promise<boolean> {
  try {
    const mode = await getStorageMode()
    return mode.mode === 'remote' && mode.remote_connected
  } catch (error) {
    return false
  }
}

/**
 * Start artifact download and return task ID
 */
export async function startArtifactDownload(
  name: string,
  version: number,
  type?: string
): Promise<string | null> {
  try {
    const result = await remoteDownloadArtifact(name, version, type)
    if (result.ok && result.task_id) {
      message.info('下载已开始')
      return result.task_id
    }
    return null
  } catch (error: any) {
    message.error(`下载失败: ${error.message}`)
    return null
  }
}

/**
 * Poll download progress until completed or failed
 */
export async function pollDownloadProgress(
  taskId: string,
  onProgress?: (progress: number, task: any) => void,
  onComplete?: (targetDir: string) => void,
  onError?: (error: string) => void
): Promise<void> {
  const poll = async () => {
    try {
      const task = await getDownloadStatus(taskId)
      
      if (onProgress) {
        onProgress(task.progress_percent, task)
      }
      
      if (task.status === 'completed') {
        if (onComplete) {
          onComplete(task.target_dir)
        }
        return true  // Stop polling
      }
      
      if (task.status === 'failed') {
        if (onError) {
          onError(task.error || '未知错误')
        }
        return true  // Stop polling
      }
      
      return false  // Continue polling
    } catch (error: any) {
      if (onError) {
        onError(error.message)
      }
      return true  // Stop polling on error
    }
  }
  
  // Poll every second until complete
  while (true) {
    const should_stop = await poll()
    if (should_stop) break
    
    // Wait 1 second before next poll
    await new Promise(resolve => setTimeout(resolve, 1000))
  }
}

/**
 * Cancel ongoing download
 */
export async function cancelArtifactDownload(taskId: string): Promise<boolean> {
  try {
    const result = await cancelDownload(taskId)
    if (result.ok) {
      message.info('下载已取消')
      return true
    }
    return false
  } catch (error: any) {
    message.error(`取消失败: ${error.message}`)
    return false
  }
}

/**
 * Format bytes to human readable format
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
}

