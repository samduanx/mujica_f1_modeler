# 命运之轮配置说明

> "The dice remember who holds them."

## 概述

本系统的核心机制受到玄学因素的微妙影响。当执行模拟时，系统会根据特定的"氛围参数"调整结果输出的概率分布。

## 氛围强度

系统支持三种氛围强度：

| 参数值 | 描述 |
|--------|------|
| subtle | 命运之轮轻微转动，结果略有偏移 |
| moderate | 命运之轮明显倾斜，倾向性显著 |
| strong | 命运之轮剧烈偏转，结果大幅倾向 |

## 目标选择

默认情况下，系统会将"关注"投向 **Ferrari** 车队。可以通过指定车队名称将关注转移至其他车队。

## 内在机制

### 骰子权重

当氛围参数激活时，20面骰(D20)的投掷结果分布将发生改变。原本均匀分布的1-20结果，将向较高数值偏移。偏移程度与氛围强度成正比。

### 失误概率

车手在比赛中犯错的概率同样受到影响。失误概率将根据目标车队的"命运值"进行平衡调整。

### 团队隔离

值得注意的是，氛围调整仅作用于被选定的目标车队。其他车队保持原有的概率特性，不受影响。

## 使用示例

```bash
# 使用PowerShell
.\scripts\run_with_assist.ps1 -Intensity moderate -TargetTeam "Ferrari"

# 使用批处理
scripts\run_with_assist.bat moderate Ferrari
```

## 直接环境变量

对于高级用户，亦可直接设置环境变量：

```cmd
set F1_NARRATIVE_ASSIST=strong
set F1_ASSIST_TARGET=Red Bull
python main.py
```

## 验证

可运行测试脚本验证系统功能：

```bash
python scripts/test_narrative_assist.py
```

测试将展示骰子分布变化、团队隔离效果及失误概率调整。
