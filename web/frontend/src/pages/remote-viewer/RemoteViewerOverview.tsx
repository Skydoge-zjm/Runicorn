import { Button, Card, Col, Row, Space, Statistic, Typography, theme } from 'antd'
import {
  CloudServerOutlined,
  SafetyCertificateOutlined,
  SaveOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

import DismissibleAlert from '../../components/DismissibleAlert'

const { Paragraph, Title } = Typography

type Props = {
  activeSessionCount: number
  connectedServers: number
  profileCount: number
  onOpenSecurity: () => void
}

export default function RemoteViewerOverview({
  activeSessionCount,
  connectedServers,
  profileCount,
  onOpenSecurity,
}: Props) {
  const { t } = useTranslation()
  const { token } = theme.useToken()

  return (
    <>
      <div style={{ flexShrink: 0, marginBottom: 16 }}>
        <Title level={2} style={{ marginBottom: 8 }}>
          <CloudServerOutlined /> {t('remote.title')}
        </Title>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          {t('remote.subtitle')}
        </Paragraph>
      </div>

      <div style={{ flexShrink: 0 }}>
        <DismissibleAlert
          alertId="remote.intro"
          type="info"
          message={t('remote.help.architecture')}
          description={t('remote.help.advantages')}
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title={t('remote.stats.activeSessions')}
                value={activeSessionCount}
                prefix={<ThunderboltOutlined />}
                valueStyle={{ color: token.colorPrimary }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title={t('remote.stats.savedConfigs')}
                value={profileCount}
                prefix={<SaveOutlined />}
                valueStyle={{ color: token.colorInfo }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title={t('remote.stats.connectedServers')}
                value={connectedServers}
                prefix={<CloudServerOutlined />}
                valueStyle={{ color: token.colorSuccess }}
              />
            </Card>
          </Col>
        </Row>

        <Space style={{ marginBottom: 16 }}>
          <Button icon={<SafetyCertificateOutlined />} onClick={onOpenSecurity}>
            {t('remote.security.advanced')}
          </Button>
        </Space>
      </div>
    </>
  )
}
