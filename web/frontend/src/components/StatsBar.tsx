import { Space, theme } from 'antd'
import { ExperimentOutlined, ThunderboltOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { RunStats } from '../hooks/useExperimentData'

interface StatsBarProps {
  stats: RunStats
}

const StatsBar: React.FC<StatsBarProps> = ({ stats }) => {
  const { t } = useTranslation()
  const { token } = theme.useToken()

  return (
    <div style={{ flexShrink: 0, marginBottom: 12 }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 12,
      }}>
        <h1 style={{
          fontSize: 20,
          fontWeight: 600,
          color: token.colorText,
          margin: 0,
        }}>
          {t('menu.experiments')}
        </h1>

        <Space size={16} style={{ flexWrap: 'wrap' }}>
          <span style={{ color: token.colorTextSecondary, fontSize: 13 }}>
            <ExperimentOutlined style={{ marginRight: 4 }} />
            {t('experiments.total_runs')}: <span style={{ fontWeight: 700, fontSize: 15, color: token.colorText }}>{stats.total}</span>
          </span>
          <span style={{ color: token.colorTextSecondary, fontSize: 13 }}>
            <ThunderboltOutlined style={{ marginRight: 4, color: token.colorWarning }} />
            {t('experiments.running')}: <span style={{ fontWeight: 700, fontSize: 15, color: token.colorWarning }}>{stats.running}</span>
          </span>
          <span style={{ color: token.colorTextSecondary, fontSize: 13 }}>
            <CheckCircleOutlined style={{ marginRight: 4, color: token.colorSuccess }} />
            {t('experiments.finished')}: <span style={{ fontWeight: 700, fontSize: 15, color: token.colorSuccess }}>{stats.finished}</span>
          </span>
          <span style={{ color: token.colorTextSecondary, fontSize: 13 }}>
            <CloseCircleOutlined style={{ marginRight: 4, color: token.colorError }} />
            {t('experiments.failed')}: <span style={{ fontWeight: 700, fontSize: 15, color: token.colorError }}>{stats.failed}</span>
          </span>
        </Space>
      </div>
    </div>
  )
}

export default StatsBar
