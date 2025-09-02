import React from 'react'
import { Card, Typography } from 'antd'
import { Link } from 'react-router-dom'

export default function ConfigPage() {
  return (
    <Card title="Runicorn Viewer (Read-only)">
      <Typography.Paragraph>
        This build is a read-only viewer for local runs stored under your runicorn storage directory.
        Starting/stopping training from the UI is not available.
      </Typography.Paragraph>
      <Typography.Paragraph>
        Go to <Link to="/runs">Runs</Link> to browse and inspect experiment metrics, logs, and GPU telemetry.
      </Typography.Paragraph>
    </Card>
  )
}
