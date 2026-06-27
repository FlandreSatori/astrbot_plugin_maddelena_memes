# astrbot_plugin_maddelena_memes

玛德蕾娜举牌表情包 AstrBot 插件。

## 功能

- 使用底图 `Maddelena.jpg` 生成举牌图
- 自动根据纸张区域自适应字号
- 支持透视贴合到倾斜纸面
- 支持 Web 配置字体、页边距、行距、字距、描边、对齐
- 支持简单富文本样式

## 指令用法

### 主命令

```text
/小画家说 [文本]
```

### 命令别名

```text
/老玛说 [文本]
/玛德蕾娜说 [文本]
```

### 示例

```text
/小画家说 test
/小画家说 第一行\n第二行
/老玛说 [color=#ff0000]红字[/color] 普通字
/玛德蕾娜说 [u]下划线[/u] [s]删除线[/s]
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

### 样式示例

```text
/小画家说 [color=#00aa88]彩色文字[/color]
/小画家说 [u]这是下划线[/u]
/小画家说 [s]这是删除线[/s]
/小画家说 [color=#ff0000][u]红色下划线[/u][/color]
```

## Web 配置项

插件支持以下配置项，可在 AstrBot 插件配置页中修改：

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

## 配置建议

- 字太小：增大 `font_max_size`，减小 `padding_x` / `padding_y`
- 多行太挤：增大 `line_spacing`
- 想增强可读性：设置 `stroke_width=1~2`，并搭配浅色 `stroke_fill`
- 想更换字体：设置 `font_path` 为本机字体文件绝对路径

## 依赖

```text
Pillow>=10.0.0
```
