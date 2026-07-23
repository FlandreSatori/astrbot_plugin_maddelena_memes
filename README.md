# astrbot_plugin_maddelena_memes

举牌表情包 AstrBot 插件，支持多模板扩展。

## 功能

- 按模板生成举牌图（透视贴合文字区域）
- 自动根据纸张区域自适应字号
- 支持 `-r` 禁用自动换行并缩小字号、`-sN` 指定字号
- 支持 Web 配置字体、页边距、行距、字距、描边、对齐
- 支持简单富文本样式

## 新增表情包（只需改这里）

1. 把底图放到 `assets/` 目录
2. 编辑 `templates.py`，追加一个 `MemeTemplate`

```python
MemeTemplate(
    id="example",                 # 唯一标识，可选
    command="某某说",              # 主触发命令
    aliases=("别名1", "别名2"),     # 可选；没有别名就整行删掉
    image="example.jpg",          # assets/ 下的文件名，或绝对路径
    text_quad=(
        (x1, y1),  # 左上
        (x2, y2),  # 右上
        (x3, y3),  # 右下
        (x4, y4),  # 左下
    ),
),
```

没有别名时写成：

```python
MemeTemplate(
    id="miaomeng",
    command="喵梦说",
    image="miaomeng.jpg",
    text_quad=(
        (x1, y1),
        (x2, y2),
        (x3, y3),
        (x4, y4),
    ),
),
```

`text_quad` 是图片像素坐标，顺序必须为：**左上 → 右上 → 右下 → 左下**。

## 指令用法

### 已内置

```text
/小画家说 [文本]
/老玛说 [文本]
/玛德蕾娜说 [文本]
```

### 可选参数

- `-r`：禁用自动换行（`\n` 手动换行仍生效），尽量缩小字号以容纳文本；若最小字号仍超出纸面范围则不显示文字
- `-sN`：指定字号，例如 `-s10` 使用 10 号字
- `-r` 与 `-s` 可叠加，例如 `-r -s10`

### 示例

```text
/小画家说 test
/小画家说 第一行\n第二行
/老玛说 -r 很长很长不换行的一句话
/老玛说 -s10 固定十号字
/老玛说 -r -s24 指定字号且不自动换行
/老玛说 [color=#ff0000]红字[/color] 普通字
```

## 支持的转义与样式

### 转义字符

- `\n`：换行
- `\t`：制表符
- `\\`：输出反斜杠
- `\[`：输出 `[`
- `\]`：输出 `]`

### 样式标记

- `[color=#ff0000]文字[/color]`：颜色
- `[u]文字[/u]`：下划线
- `[s]文字[/s]`：删除线

## Web 配置项

- `padding_x`：左右页边距
- `padding_y`：上下页边距
- `line_spacing`：行间距
- `char_spacing`：字间距
- `font_min_size`：最小字号
- `font_max_size`：最大字号
- `font_path`：自定义字体文件路径
- `text_color`：默认文字颜色
- `stroke_width`：描边宽度
- `stroke_fill`：描边颜色
- `align`：水平对齐，可选 `left` / `center` / `right`

## 目录结构

```text
astrbot_plugin_maddelena_memes/
├── assets/           # 底图放这里
├── templates.py      # 只需改这个文件来新增模板
├── meme_spec.py      # 模板数据结构
├── render.py         # 渲染引擎
├── main.py           # 插件入口
└── ...
```

## 依赖

```text
Pillow>=10.0.0
```
