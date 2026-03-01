# Mujica_F1_Modeler

## Introduction | 简介
### English
This is the simulation system codes for Formula 1 races, prepared for the author's BanG Dream! MyGO and Ave Mujica and also Formula 1 anchor-based fan-fiction in the Chinese netforum NGA named *Ave velocita*.

The previous system used an Excel spreadsheet (like what the Williams team used before) for the simulation. This version on GitHub provides a more integrated, mathematically reliable, and readable approach to the simulation.

The system is created **almost entirely by vibe coding techniques**, therefore reliability cannot be assured. The coding is powered by Minimax M2.1, Kimi K2 and 2.5, and also GLM 4.6. Data of tracks and races are from Pirelli and analysis based on data from FastF1. Data may have copyright.

* Anchor based fanfics are created with the guidance of multiple dice rollings, providing a form similar to a board game and allowing readers to experience some sorts of randomness and the thrill of unexpected events. *Ave velocita* has adopted this system to a extent where dice rolls are used to create not only the stories but also the racing simulations.

* This also means the fan-fic based on these codes will create races in a vastly different way from the previous chapters. Viewer discretion is advised.

* For users and developers not knowing Chinese, due to the vibe coding process are mostly instructed in Chinese, documents created by the LLMs are also mostly in Chinese.

---

### Chinese
本程序是NGA论坛安科《大祥老师，用你的惊世智慧拯救法拉利车队吧！》（预计不久之后就会改名为竞速颂歌/Ave velocita）使用的新版本的赛事模拟系统。

《竞速颂歌》的旧版赛事模拟器是通过一个威廉姆斯车队同款Excel表实现的。为了增强集成性、数学可靠性和（含骰点）的数据可读性，我们采用了本repo中的方式重构了模拟系统。

本模拟系统的代码**几乎全部由vibe coding完成**，主要使用Minimax M2.1实现，同时使用了Kimi K2、K2.5及GLM 4.6等模型。部分赛道数据来自Pirelli，部分来自对FastF1数据的直接分析。数据可能存在版权问题。

* 安科的具体定义可以在NGA安科版的置顶贴中找到，总而言之，安科是通过设定选择枝并以骰点方式随机选择选择枝的方式推进的同人或原创作品。《竞速颂歌》现有的系统中，除了用于处理剧情选择枝（含读者提供的安价），还用于进行赛事模拟。

* 本安科在采用本工程建立的新系统后，生成的比赛过程会与过去版本产生巨大的差异。对此产生的不便敬请谅解。

* 部分文档由于Zed editor及后续更换工具后使用的agent prompt原因，会使用英文。

## 运行

### 大奖赛模拟

````
python main.py --gp-name 大奖赛名称
````

## TODO
- [x] 基本模型 | Basic features
  - [x] 基本圈速模拟与车手差异构建 | Basic laptime simulations and driver differention modeling
  - [x] 轮胎差异模拟 | Tyre differention simulations
  - [x] 赛道特性构建 | Circuit characteristic modeling
  - [ ] 轮胎套数限制模型构建 | Tyre overall usage (by sets) limit modeling
  - [x] DR, PR计算系统 | Calculation system of DR and PR parameters
    - [ ] 车队升级机制移植 | Porting the current team/vehicle upgrades
    - [ ] 车手技能提升机制移植 | Porting the current driver upgrades
- [ ] 自由练习 | Free Practice sessions
- [ ] 排位赛（含冲刺排位） | Qualifying sessions (incl. Sprint Qualifiers)
- [ ] 冲刺赛 | Sprint sessions
- [ ] 正赛 | Races
  - [x] 进站模拟 | Pit stop simulations
  - [x] 发车模拟 | Grid and start simulations
  - [x] 斗车、超车、DRS模拟 | Simulations of car battling, overtaking, and DRS usage
  - [x] 事故、红黄旗、（虚拟）安全车模拟 | Simulations of accidents, red/yellow flags, and (V)SC
  - [ ] 违规与处罚 | Penalties
  - [ ] 天气系统 | Weathering system
  - [x] 蓝旗（套圈）处理 | Simulation of lapping (blue flags)
- [ ] 赛后内容 | After-race info
  - [x] 赛事记录文档（含骰点）导出方法 | Exports of race records (including dice rolls)
  - [ ] 积分榜 | Leaderboards
  - [ ] 罚分处理 | Penalty processing and point calculations
  - [ ] 预算帽计算方法移植 | Porting the cost cap system
  - [ ] 套件更换与处罚计算 | Modeling of sanctioned part replacements and related penalties

---

## Changelog | 更新日志

### v2.x Breaking Changes (2025+)

- **Output filename format changed**: Race result files now use `{track}.csv` instead of `{track}_{year}.csv`
  - Old: `race_results_spain_2024.csv`
  - New: `race_results_spain.csv`
  - `--year` CLI parameter removed from simulation scripts

---

* 新功能的提出，或bug修复，请通过issue提出。
* 开发时，请使用uv进行环境配置。程序开发和运行均在Python 3.11中进行（来自asdf）。

* Please submit issues regarding to new features or bug fixes.
* Please use uv for Python environment configuration. Codes are developed and tested on Python 3.11 (from asdf).
