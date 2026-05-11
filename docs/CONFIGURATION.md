# 🔔 Jingle 配置说明（v1）

从 v26.2 开始，`config/bells.conf` 必须是带版本字段的 JSON。

```json
{
  "version": "v1",
  "collections": {},
  "presets": {},
  "entries": []
}
```

## 1) 版本字段
- `version` 必填，当前仅支持 `v1`
- 缺失或不支持的版本会被解析器立即拒绝

## 2) collections（收藏集）
- 命名的可复用歌曲池
- 值是字符串数组，可包含文件名或通配符（`*`、`?`）
- 在 `entries[].sources` 中通过 `@name` 引用

## 3) presets（预设）
支持两种模式：

### times 模式
```json
{
  "mode": "times",
  "days": [1,2,3,4,5],
  "times": ["08:00", "12:00", "18:00"]
}
```

### all_day 模式
```json
{
  "mode": "all_day",
  "days": [],
  "start": "00:00",
  "end": "23:59",
  "interval_minutes": 60
}
```

## 4) entries（调度条目）
- `preset`：可选，引用 `presets` 名称
- `days`：可选，留空表示每天；若有 `preset.days`，会作为默认值
- `times`：可选，留空时可使用 `preset` 的时间配置
- `sources`：必填，支持普通文件名、通配符、`@收藏集`

时间支持：
- `HH:MM`
- `-HH:MM`（禁用）
- `HH:MM-HH:MM`（时间段）

## 5) 迁移旧配置
旧语法只用于一次性迁移，不再作为运行时格式：

```bash
python migrate_config.py
```

默认会生成 `config/bells.legacy.bak` 备份。
