import React, { useMemo } from 'react'
import { Card, Empty, Space, Tag, Typography } from 'antd'
import { DatabaseOutlined, ThunderboltOutlined, ArrowRightOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useTranslation } from 'react-i18next'
import designTokens from '../styles/designTokens'

const { Text } = Typography

interface LineageGraphProps {
  data: {
    root_artifact: string
    nodes: Array<{
      node_type: string  // 'artifact' or 'run'
      node_id: string
      label: string
      metadata: Record<string, any>
    }>
    edges: Array<{
      source: string
      target: string
      edge_type: string  // 'uses' or 'produces'
    }>
  }
}

const LineageGraph: React.FC<LineageGraphProps> = ({ data }) => {
  const { t } = useTranslation()

  // Convert data to ECharts graph format
  const chartOption = useMemo(() => {
    if (!data || !data.nodes || data.nodes.length === 0) {
      return null
    }

    // Build nodes
    const nodes = data.nodes.map(node => {
      const isArtifact = node.node_type === 'artifact'
      const isRoot = node.node_id === data.root_artifact
      
      return {
        id: node.node_id,
        name: node.label,
        symbol: isArtifact ? 'roundRect' : 'circle',
        symbolSize: isRoot ? [120, 60] : (isArtifact ? [100, 50] : 40),
        label: {
          show: true,
          fontSize: isRoot ? 14 : 12,
          fontWeight: isRoot ? 'bold' : 'normal',
        },
        itemStyle: {
          color: isArtifact 
            ? (isRoot ? designTokens.colors.primary : designTokens.colors.info)
            : designTokens.colors.success,
          borderColor: isRoot ? designTokens.colors.primary : '#fff',
          borderWidth: isRoot ? 3 : 1,
        },
        category: isArtifact ? 0 : 1,
      }
    })

    // Build edges
    const edges = data.edges.map(edge => ({
      source: edge.source,
      target: edge.target,
      label: {
        show: true,
        formatter: edge.edge_type,
        fontSize: 10,
      },
      lineStyle: {
        color: edge.edge_type === 'produces' 
          ? designTokens.colors.success 
          : designTokens.colors.info,
        width: 2,
        type: edge.edge_type === 'produces' ? 'solid' : 'dashed',
      },
      symbol: ['none', 'arrow'],
      symbolSize: 8,
    }))

    return {
      title: {
        text: t('artifact.lineage.title'),
        left: 'center',
        textStyle: {
          fontSize: designTokens.typography.fontSize.lg,
          fontWeight: designTokens.typography.fontWeight.semibold,
        },
      },
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          if (params.dataType === 'node') {
            const node = data.nodes.find(n => n.node_id === params.data.id)
            if (node) {
              const isArtifact = node.node_type === 'artifact'
              let content = `<b>${node.label}</b><br/>`
              content += `Type: ${isArtifact ? t('artifact.lineage.node.artifact') : t('artifact.lineage.node.run')}<br/>`
              
              if (node.metadata.size) {
                const size = formatBytes(node.metadata.size)
                content += `Size: ${size}<br/>`
              }
              
              return content
            }
          } else if (params.dataType === 'edge') {
            return `${params.data.label.formatter}`
          }
          return params.name
        },
      },
      legend: {
        data: [
          {
            name: t('artifact.lineage.node.artifact'),
            icon: 'roundRect',
          },
          {
            name: t('artifact.lineage.node.run'),
            icon: 'circle',
          },
        ],
        bottom: 0,
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          data: nodes,
          links: edges,
          categories: [
            { name: t('artifact.lineage.node.artifact') },
            { name: t('artifact.lineage.node.run') },
          ],
          roam: true,
          label: {
            show: true,
            position: 'inside',
            formatter: '{b}',
          },
          force: {
            repulsion: 400,
            edgeLength: [120, 180],
            gravity: 0.1,
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: {
              width: 4,
            },
          },
        },
      ],
    }
  }, [data, t])

  // Helper function
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
  }

  if (!chartOption) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={t('artifact.lineage.no_dependencies')}
      />
    )
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {/* Legend Explanation */}
      <Card size="small">
        <Space split={<span style={{ margin: '0 12px', color: '#d9d9d9' }}>•</span>}>
          <Space size="small">
            <DatabaseOutlined style={{ color: designTokens.colors.info }} />
            <Text type="secondary" style={{ fontSize: designTokens.typography.fontSize.xs }}>
              {t('artifact.lineage.node.artifact')}
            </Text>
          </Space>
          <Space size="small">
            <ThunderboltOutlined style={{ color: designTokens.colors.success }} />
            <Text type="secondary" style={{ fontSize: designTokens.typography.fontSize.xs }}>
              {t('artifact.lineage.node.run')}
            </Text>
          </Space>
          <Space size="small">
            <ArrowRightOutlined style={{ color: designTokens.colors.info }} />
            <Text type="secondary" style={{ fontSize: designTokens.typography.fontSize.xs }}>
              {t('artifact.lineage.edge.uses')}
            </Text>
          </Space>
          <Space size="small">
            <ArrowRightOutlined style={{ color: designTokens.colors.success }} />
            <Text type="secondary" style={{ fontSize: designTokens.typography.fontSize.xs }}>
              {t('artifact.lineage.edge.produces')}
            </Text>
          </Space>
        </Space>
      </Card>

      {/* Graph */}
      <Card>
        <ReactECharts
          option={chartOption}
          style={{ height: 500 }}
          opts={{ renderer: 'canvas' }}
        />
      </Card>

      {/* Summary */}
      <Card size="small">
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Text type="secondary" style={{ fontSize: designTokens.typography.fontSize.xs }}>
            <b>{t('Summary')}:</b> {data.nodes.length} nodes, {data.edges.length} edges
          </Text>
          <Text type="secondary" style={{ fontSize: designTokens.typography.fontSize.xs }}>
            • Artifacts: {data.nodes.filter(n => n.node_type === 'artifact').length}
          </Text>
          <Text type="secondary" style={{ fontSize: designTokens.typography.fontSize.xs }}>
            • Runs: {data.nodes.filter(n => n.node_type === 'run').length}
          </Text>
        </Space>
      </Card>
    </Space>
  )
}

export default LineageGraph

