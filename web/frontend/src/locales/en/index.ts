import common from './common'
import experiments from './experiments'
import artifacts from './artifacts'
import remoteStorage from './remote-storage'
import settings from './settings'

export default {
  ...common,
  ...experiments,
  ...artifacts,
  ...remoteStorage,
  ...settings,
}

