// 从课本/课标 md 提取物理术语, 生成语音识别热词表
import fs from 'node:fs/promises';
import path from 'node:path';

const WS = process.argv[2] || '.';
const OUT = path.join(WS, '流水线文档', '物理术语表.txt');

const SOURCES = [
  '8上-苏科版版初中物理课本（2024新版）.md',
  '8下-苏科版初中物理课本（2025新版）.md',
];

// 人工种子词: 口播里高频、且语音识别最容易听错的
const SEED = `
受力分析 二力平衡 平衡力 相互作用力 惯性 牛顿第一定律 牛顿第二定律 惯性定律
摩擦力 滑动摩擦 滚动摩擦 静摩擦 重力 弹力 支持力 拉力 压力 阻力 合力 分力 力的示意图
匀速直线运动 变速运动 参照物 机械运动 运动状态 速度 平均速度 路程 位移 加速度
质量 密度 体积 天平 量筒 排水法
压强 液体压强 大气压 标准大气压 帕斯卡 连通器 托里拆利实验 流体压强 流速
浮力 阿基米德原理 漂浮 悬浮 下沉 排开液体 密度计 潜水艇
杠杆 支点 动力臂 阻力臂 省力杠杆 费力杠杆 等臂杠杆 滑轮 定滑轮 动滑轮 滑轮组 斜面
功 功率 机械效率 有用功 额外功 总功 焦耳
动能 重力势能 弹性势能 机械能 能量守恒 能量转化
内能 热量 比热容 热传递 做功 热机 内燃机 热值 效率
熔化 凝固 汽化 液化 升华 凝华 温度 摄氏度 温度计 晶体 非晶体 熔点 沸点 蒸发 沸腾
分子 原子 分子热运动 扩散现象 分子间作用力 纳米
电荷 正电荷 负电荷 摩擦起电 电流 电压 电阻 电路 串联 并联 短路 断路 通路
欧姆定律 电流表 电压表 滑动变阻器 定值电阻 电功 电功率 千瓦时 焦耳定律 家庭电路 保险丝 三孔插座
磁场 磁感线 磁极 电磁铁 电磁继电器 通电导线 电磁感应 发电机 电动机 地磁场 奥斯特实验 法拉第
光 光源 光的直线传播 小孔成像 光的反射 镜面反射 漫反射 平面镜成像 光的折射 光的色散
凸透镜 凹透镜 焦点 焦距 实像 虚像 放大 缩小 正立 倒立 照相机 投影仪 放大镜 近视眼 远视眼 眼镜
声音 声源 声音的产生 声音的传播 声速 响度 音调 音色 超声波 次声波 噪声 回声 回声测距
刻度尺 秒表 弹簧测力计 砝码 温度计 电流表 电压表 显微镜 望远镜
物理 力学 热学 光学 声学 电学 磁学 能量 压强 实验 探究 控制变量法 转换法 类比法 理想实验法
苏科版 沪科版 人教版 北师大版
`.trim();

const set = new Set();
const seedOrder = [];
for (const w of SEED.split(/\s+/)) {
  const t = w.trim();
  if (t.length >= 2) {
    if (!set.has(t)) seedOrder.push(t);
    set.add(t);
  }
}

// 从标题里提取章节名
let headingCount = 0;
for (const f of SOURCES) {
  let text;
  try {
    text = await fs.readFile(path.join(WS, f), 'utf8');
  } catch {
    continue;
  }
  for (const line of text.split(/\r?\n/)) {
    const m = line.match(/^#{1,4}\s+(.+)$/);
    if (!m) continue;
    let h = m[1]
      .replace(/[`*_>]/g, '')
      .replace(/[（(].*?[)）]/g, '')
      .replace(/^\s*第[一二三四五六七八九十百]+[章节讲]\s*/, '')
      .replace(/[、,，.。:：;；!！?？"'"'《》〈〉\[\]【】]/g, ' ')
      .trim();
    if (!h || h.length > 24) continue;
    if (/^[\d\s生第页]+$/.test(h)) continue;
    for (const part of h.split(/\s+/)) {
      const t = part.trim();
      // 只要真正的「术语」: 长度 2-8, 不含虚词/句子成分
      const bad = /[的了着过与和及或在为是对以把被这那不并且使让把从由当]/;
      if (
        t.length >= 2 &&
        t.length <= 8 &&
        /^[\u4e00-\u9fa5]+$/.test(t) &&
        !bad.test(t) &&
        !/^(探究|观察|了解|认识|理解|运用|分析|学会|知道|经历|体验|培养|注重|围绕|基于|利用|建立|形成|具有|初次)/.test(t)
      ) {
        set.add(t);
        headingCount++;
      }
    }
  }
}

// 人工种子词排在最前(它们对口播最有用, 且只会用到前 300 字), 其余按长度降序
const rest = [...set]
  .filter((t) => !seedOrder.includes(t))
  .sort((a, b) => b.length - a.length || a.localeCompare(b, 'zh'));
const terms = [...seedOrder, ...rest];
await fs.mkdir(path.dirname(OUT), { recursive: true });
await fs.writeFile(
  OUT,
  `# 初中物理语音识别热词表\n# 生成时间: ${new Date().toISOString().slice(0, 16).replace('T', ' ')}\n# 来源: 苏科版八上/八下课本 + 2022新课标(物理/科学) + 人工补充\n# 共 ${terms.length} 条\n\n` +
    terms.join('\n') +
    '\n',
  'utf8'
);

console.log(`术语表已生成: ${OUT}`);
console.log(`共 ${terms.length} 条 (标题提取 ${headingCount} 处, 种子词 ${SEED.split(/\s+/).length} 条)`);
console.log('样例: ' + terms.slice(0, 25).join(' / '));
