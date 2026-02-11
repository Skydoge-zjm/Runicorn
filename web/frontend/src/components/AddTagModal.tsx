import React, { useState, useEffect, useMemo } from 'react'
import { Modal, Input, Button, Tag, Space, Typography, Divider } from 'antd'
import { useTranslation } from 'react-i18next'

const { Text } = Typography

// Preset recommended tags
const RECOMMENDED_TAGS = [
  'baseline',
  'best',
  'experiment',
  'debug',
  'production',
  'test',
  'v1',
  'v2',
  'final',
  'draft',
]

interface AddTagModalProps {
  open: boolean
  onClose: () => void
  onConfirm: (tag: string) => void
  existingTags: string[]
  allTags: string[]
}

const AddTagModal: React.FC<AddTagModalProps> = ({
  open,
  onClose,
  onConfirm,
  existingTags,
  allTags,
}) => {
  const { t } = useTranslation()
  const [inputValue, setInputValue] = useState('')

  useEffect(() => {
    if (open) {
      setInputValue('')
    }
  }, [open])

  const historyTags = useMemo(() => {
    const uniqueTags = [...new Set(allTags)]
    return uniqueTags
      .filter(tag => !existingTags.includes(tag) && !RECOMMENDED_TAGS.includes(tag))
      .slice(0, 10)
  }, [allTags, existingTags])

  const recommendedTags = useMemo(() => {
    return RECOMMENDED_TAGS.filter(tag => !existingTags.includes(tag))
  }, [existingTags])

  const handleConfirm = () => {
    const trimmed = inputValue.trim()
    if (trimmed) {
      onConfirm(trimmed)
      setInputValue('')
    }
  }

  const handleTagClick = (tag: string) => {
    onConfirm(tag)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleConfirm()
    } else if (e.key === 'Escape') {
      onClose()
    }
  }

  return (
    <Modal
      title={t('experiments.add_tag_title') || 'Add Tag'}
      open={open}
      onCancel={onClose}
      footer={[
        <Button key="cancel" onClick={onClose}>
          {t('common.cancel') || 'Cancel'}
        </Button>,
        <Button 
          key="confirm" 
          type="primary" 
          onClick={handleConfirm}
          disabled={!inputValue.trim()}
        >
          {t('common.confirm') || 'Confirm'}
        </Button>,
      ]}
      width={400}
      destroyOnHidden
    >
      <div style={{ marginBottom: 16 }}>
        <Input
          placeholder={t('experiments.enter_tag') || 'Enter tag name...'}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          autoFocus
          size="large"
        />
      </div>

      {historyTags.length > 0 && (
        <>
          <Divider style={{ margin: '12px 0 8px' }} />
          <div>
            <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
              {t('experiments.history_tags') || 'History Tags'}
            </Text>
            <Space size={[4, 8]} wrap>
              {historyTags.map(tag => (
                <Tag
                  key={tag}
                  style={{ cursor: 'pointer' }}
                  onClick={() => handleTagClick(tag)}
                >
                  {tag}
                </Tag>
              ))}
            </Space>
          </div>
        </>
      )}

      {recommendedTags.length > 0 && (
        <>
          <Divider style={{ margin: '12px 0 8px' }} />
          <div>
            <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
              {t('experiments.recommended_tags') || 'Recommended Tags'}
            </Text>
            <Space size={[4, 8]} wrap>
              {recommendedTags.map(tag => (
                <Tag
                  key={tag}
                  color="blue"
                  style={{ cursor: 'pointer' }}
                  onClick={() => handleTagClick(tag)}
                >
                  {tag}
                </Tag>
              ))}
            </Space>
          </div>
        </>
      )}
    </Modal>
  )
}

export default AddTagModal
