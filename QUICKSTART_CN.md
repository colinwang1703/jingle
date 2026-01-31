# Jingle 快速入门指南

一个专为资源受限设备（如树莓派Zero）设计的轻量级定时音乐播放系统。

## 功能特点

✅ **极简资源占用** - 优化的音频后端，确保在低配硬件上稳定运行
✅ **灵活配置** - 支持YAML/JSON配置文件和环境变量
✅ **热更新** - 无需重启即可更新配置
✅ **扩展触发** - 支持时间触发和事件触发
✅ **REST API** - 通过HTTP接口远程控制
✅ **模块化设计** - 易于维护和扩展

## 快速安装

### 在树莓派上安装

```bash
# 更新系统
sudo apt-get update

# 安装依赖
sudo apt-get install -y python3-pip python3-dev libsdl2-mixer-2.0-0 libsdl2-2.0-0

# 克隆项目
git clone https://github.com/colinwang1703/jingle.git
cd jingle

# 安装Python依赖
pip3 install -r requirements.txt
```

## 基础使用

### 1. 准备音乐文件

```bash
# 创建音乐目录
mkdir music

# 复制音乐文件到music目录
cp /path/to/your/music/*.mp3 music/
```

### 2. 配置定时播放

编辑 `config/jingle.yaml`：

```yaml
# 播放器设置
player:
  music_dir: "./music"    # 音乐文件目录
  volume: 0.7             # 音量 (0.0 到 1.0)

# 定时播放计划
schedules:
  # 每天早上8点播放
  - time: "08:00"
    music: "morning.mp3"
    options:
      fade_in: 2.0        # 淡入2秒
  
  # 每天中午12点播放
  - time: "12:00"
    music: "lunch.mp3"
    options:
      fade_in: 1.0
  
  # 每天晚上6点播放
  - time: "18:00"
    music: "evening.mp3"
    options:
      fade_in: 2.0
  
  # 每2小时播放一次
  - time: "every 2 hours"
    music: "reminder.mp3"
  
  # 每30分钟播放一次
  - time: "every 30 minutes"
    music: "chime.mp3"
```

### 3. 运行程序

```bash
# 基础运行
python3 -m jingle.main -c config/jingle.yaml

# 开启详细日志
python3 -m jingle.main -c config/jingle.yaml -v

# 禁用热更新
python3 -m jingle.main -c config/jingle.yaml --no-hot-reload
```

## 高级功能

### REST API 远程控制

#### 安装API依赖

```bash
pip3 install -r requirements-api.txt
```

#### 启动API服务器

```bash
python3 -m jingle.api -c config/jingle.yaml
```

#### API使用示例

**立即播放音乐：**
```bash
curl -X POST http://localhost:5000/api/play \
  -H "Content-Type: application/json" \
  -d '{"music": "morning.mp3", "fade_in": 2.0}'
```

**调整音量：**
```bash
curl -X POST http://localhost:5000/api/volume \
  -H "Content-Type: application/json" \
  -d '{"volume": 0.5}'
```

**添加新的定时计划：**
```bash
curl -X POST http://localhost:5000/api/schedules \
  -H "Content-Type: application/json" \
  -d '{"time": "every 30 minutes", "music": "chime.mp3"}'
```

**停止播放：**
```bash
curl -X POST http://localhost:5000/api/stop \
  -H "Content-Type: application/json" \
  -d '{"fade_out": 1.0}'
```

**查看状态：**
```bash
curl http://localhost:5000/api/status
```

### Python编程接口

```python
from jingle import ConfigManager, AudioPlayer, MusicScheduler

# 初始化组件
player = AudioPlayer(music_dir='./music', volume=0.7)
scheduler = MusicScheduler(player=player)

# 添加定时播放
scheduler.add_schedule("09:00", "morning.mp3", fade_in=2.0)
scheduler.add_schedule("every 1 hour", "reminder.mp3")

# 启动调度器
scheduler.start()

# 添加事件触发器（例如：传感器触发）
def on_sensor_trigger():
    player.play("alert.mp3")

scheduler.add_event_handler("sensor_trigger", on_sensor_trigger)

# 触发事件
scheduler.trigger_event("sensor_trigger")
```

### 设置为系统服务

#### 创建服务文件

```bash
# 复制服务配置
sudo cp examples/jingle.service /etc/systemd/system/

# 如需API服务
sudo cp examples/jingle-api.service /etc/systemd/system/
```

#### 启动服务

```bash
# 重新加载systemd配置
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable jingle.service

# 启动服务
sudo systemctl start jingle.service

# 查看状态
sudo systemctl status jingle.service

# 查看日志
sudo journalctl -u jingle.service -f
```

## 配置说明

### 时间格式

**固定时间：**
- `"08:00"` - 每天早上8点
- `"13:30"` - 每天下午1点30分
- `"23:59"` - 每天晚上11点59分

**间隔时间：**
- `"every 30 minutes"` - 每30分钟
- `"every 1 hour"` - 每1小时
- `"every 2 hours"` - 每2小时
- `"every 10 seconds"` - 每10秒（用于测试）

### 播放选项

```yaml
options:
  fade_in: 2.0      # 淡入时长（秒）
  fade_out: 1.0     # 淡出时长（秒）
  loops: 0          # 循环次数（0=播放一次，-1=无限循环）
```

### 环境变量覆盖

```bash
# 覆盖音量设置
export JINGLE_VOLUME=0.5

# 覆盖音乐目录
export JINGLE_MUSIC_DIR=/home/pi/my-music

# 运行程序
python3 -m jingle.main -c config/jingle.yaml
```

## 支持的音频格式

- MP3 (.mp3)
- WAV (.wav)
- OGG (.ogg)
- FLAC (.flac)
- M4A (.m4a)
- AAC (.aac)

## 性能优化

### 树莓派Zero优化建议

1. **使用MP3格式** - 相比FLAC体积小，解码快
2. **调整热更新间隔** - 减少文件系统检查频率
   ```bash
   python3 -m jingle.main -c config.yaml --reload-interval 10
   ```
3. **降低音频质量** - 如果音质要求不高，使用较低比特率的音频文件
4. **减少并发任务** - 避免同时运行多个定时任务

## 故障排除

### 无声音输出

```bash
# 测试音频设备
speaker-test -t wav

# 检查音量
alsamixer

# 检查音乐文件路径
ls -la music/
```

### 服务无法启动

```bash
# 查看详细错误日志
sudo journalctl -u jingle.service -n 50

# 手动运行测试
python3 -m jingle.main -c config/jingle.yaml -v
```

### 配置未生效

```bash
# 检查配置文件语法
python3 -c "import yaml; yaml.safe_load(open('config/jingle.yaml'))"

# 确认文件权限
ls -l config/jingle.yaml
```

## 示例场景

### 场景1: 学校/公司定时播放音乐

```yaml
schedules:
  - time: "08:00"
    music: "morning_bell.mp3"    # 上午上课铃
  - time: "12:00"
    music: "lunch_bell.mp3"      # 午餐铃
  - time: "18:00"
    music: "evening_bell.mp3"    # 下班铃
```

### 场景2: 智能家居整点报时

```yaml
schedules:
  - time: "every 1 hour"
    music: "chime.mp3"
    options:
      fade_in: 0.5
```

### 场景3: 商店背景音乐

```yaml
player:
  volume: 0.3    # 背景音乐音量较低

schedules:
  - time: "09:00"
    music: "playlist_morning.mp3"
    options:
      loops: -1    # 循环播放
```

### 场景4: 传感器触发播放（配合Python代码）

```python
# sensor_trigger.py
from jingle import AudioPlayer, MusicScheduler
import RPi.GPIO as GPIO

player = AudioPlayer(music_dir='./music')
scheduler = MusicScheduler(player=player)

# 设置GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# 定义触发器
def on_button_press(channel):
    print("按钮被按下！")
    player.play("alert.mp3", fade_in=0.5)

# 绑定事件
GPIO.add_event_detect(17, GPIO.FALLING, callback=on_button_press, bouncetime=300)

# 保持运行
scheduler.start()
try:
    while True:
        pass
except KeyboardInterrupt:
    GPIO.cleanup()
```

## 获取帮助

- 查看完整文档: `README.md`
- 查看演示文档: `DEMO.md`
- 查看示例代码: `examples/`
- GitHub Issues: https://github.com/colinwang1703/jingle/issues

## 许可证

MIT License - 详见 LICENSE 文件
