import React, { useEffect, useMemo } from 'react'
import { Button, Col, Form, Input, InputNumber, Row, Select, Switch, Tooltip, Collapse } from 'antd'

const models = [
  { label: 'LeNet', value: 'lenet' },
  { label: 'ResNet18', value: 'resnet18' },
  { label: 'ResNet34', value: 'resnet34' },
  { label: 'ResNet50', value: 'resnet50' },
  { label: 'ResNet101', value: 'resnet101' },
  { label: 'ViT Tiny', value: 'vit_tiny' },
  { label: 'ViT Small', value: 'vit_small' },
  { label: 'ViT Base', value: 'vit_base' },
]

const datasets = [
  { label: 'CIFAR-10', value: 'cifar10' },
  { label: 'ImageNet-1K', value: 'imagenet' },
]

export default function RunConfigForm({ onSubmit, submitting }: { onSubmit: (v: any) => void; submitting: boolean }) {
  const [form] = Form.useForm()

  const defaultValues = useMemo(() => ({
    model: 'vit_tiny',
    dataset: 'cifar10',
    epochs: 10,
    batchSize: 128,
    lr: 0.0005,
    numWorkers: 4,
    amp: false,
    saveEachEpoch: false,
    newThreadTest: false,
    mode: undefined as string | undefined,
    monitor: 'val_acc',
    monitorMode: 'max',
    topkKeep: 3,
    pythonExec: 'E:\\Anaconda\\envs\\pytorch\\python.exe',
  }), [])

  const persisted = useMemo(() => {
    try { return JSON.parse(localStorage.getItem('run_form_values') || 'null') || {} } catch { return {} }
  }, [])

  useEffect(() => {
    form.setFieldsValue({ ...defaultValues, ...persisted })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const mode = Form.useWatch('mode', form)

  const handleValuesChange = (_: any, allValues: any) => {
    try { localStorage.setItem('run_form_values', JSON.stringify(allValues)) } catch {}
  }

  return (
    <Form form={form} layout="vertical" onFinish={onSubmit} onValuesChange={handleValuesChange}>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item name="model" label="Model" rules={[{ required: true, message: 'Please select a model' }]}>
            <Select options={models} showSearch optionFilterProp="label" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="dataset" label="Dataset" rules={[{ required: true, message: 'Please select a dataset' }]}>
            <Select options={datasets} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="epochs" label={
            <span>
              Train Epochs <Tooltip title="Training config only. Viewer metrics use step/time with stage separators."><span style={{ color: '#999' }}>ⓘ</span></Tooltip>
            </span>
          } rules={[{ required: true, message: 'Train epochs is required' }]}
          >
            <InputNumber min={1} step={1} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item name="batchSize" label={
            <span>
              Batch Size <Tooltip title="Per-step batch size; use grad accumulation in config to emulate larger batch if needed."><span style={{ color: '#999' }}>ⓘ</span></Tooltip>
            </span>
          } rules={[{ required: true, message: 'Batch size is required' }]}
          >
            <InputNumber min={1} step={1} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="lr" label={
            <span>
              Learning Rate <Tooltip title="Base learning rate for optimizer"><span style={{ color: '#999' }}>ⓘ</span></Tooltip>
            </span>
          } rules={[{ required: true, message: 'LR is required' }]}
          >
            <InputNumber min={0.0000001} step={0.0001} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="numWorkers" label="Num Workers" rules={[{ required: true, message: 'Workers is required' }]}>
            <InputNumber min={0} step={1} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item name="amp" label="AMP" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="saveEachEpoch" label={
            <span>
              Save Each Epoch <Tooltip title="Training checkpointing option; does not affect viewer metrics"><span style={{ color: '#999' }}>ⓘ</span></Tooltip>
            </span>
          } valuePropName="checked">
            <Switch />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="newThreadTest" label="Async Validation" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item name="mode" label="Mode">
            <Select allowClear options={[
              { label: 'timm_in1k', value: 'timm_in1k' },
              { label: 'scratch', value: 'scratch' },
              { label: 'timm_in21k', value: 'timm_in21k' },
              { label: 'checkpoint', value: 'checkpoint' },
            ]} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="dataRoot" label="Data Root">
            <Input placeholder="./data" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="seed" label="Seed">
            <InputNumber min={0} step={1} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        {mode === 'timm_in21k' && (
          <Col span={12}>
            <Form.Item name="pretrainedPath" label="Pretrained Path (timm cache)">
              <Input placeholder="e.g. ./data/vit_timm_in21k_pretrained" />
            </Form.Item>
          </Col>
        )}
        {mode === 'checkpoint' && (
          <Col span={12}>
            <Form.Item name="checkpointPath" label="Checkpoint Path">
              <Input placeholder="e.g. ./checkpoints/xxx/best_model.pth" />
            </Form.Item>
          </Col>
        )}
      </Row>

      <Collapse style={{ marginTop: 8 }} items={[{
        key: 'adv',
        label: 'Advanced Settings',
        children: (
          <>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="monitor" label="Monitor Metric">
                  <Input placeholder="val_acc" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="monitorMode" label="Monitor Mode">
                  <Select options={[{ label: 'max', value: 'max' }, { label: 'min', value: 'min' }]} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="topkKeep" label="Top-K Keep">
                  <InputNumber min={1} step={1} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="pythonExec" label="Python Executable">
                  <Input placeholder="E:\\Anaconda\\envs\\pytorch\\python.exe" />
                </Form.Item>
              </Col>
            </Row>
          </>
        )
      }]} />
      <Row>
        <Col span={24}>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={submitting}>Start</Button>
          </Form.Item>
        </Col>
      </Row>
    </Form>
  )
}
