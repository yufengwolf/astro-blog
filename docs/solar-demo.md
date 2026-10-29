# 太阳系 3D 模型

下面是通过 `iframe` 嵌入的 Three.js 太阳系实时模型（构建产物 + iframe，方案 A）。点右上角「全屏」可铺满屏幕查看；手机端全屏建议横屏。

<div class="solar-embed" id="solar-embed">
  <div class="solar-bar">
    <span class="solar-title">太阳系 3D 实时模型</span>
    <button type="button" class="solar-fs-btn" id="solar-fs-btn">全屏</button>
  </div>
  <div class="solar-frame">
    <iframe src="https://astro-solar-3d.pages.dev/" title="太阳系 3D 实时模型" loading="lazy" allowfullscreen allow="fullscreen"></iframe>
    <div class="solar-rotate">
      <span class="solar-rotate-icon">↻</span>
      请旋转手机至横屏，获得更大的观测视野
    </div>
  </div>
</div>

- 鼠标拖拽旋转视角，滚轮缩放。
- 悬停行星会出现白色描边，点击行星相机飞近并弹出资料卡。
- 右上角面板可调节公转 / 自转速度、太阳亮度。
- 想更大？点上方「全屏」按钮，再点一次或按 Esc 退出。

子系统：[地月](/earth-moon/) · [火星](/mars-system/) · [木星](/jupiter-system/) · [土星](/saturn-system/) · [天王星](/uranus-system/) · [海王星](/neptune-system/) · [冥王星](/pluto-system/)

如果上面的窗口没有显示，可直接打开 [astro-solar-3d.pages.dev](https://astro-solar-3d.pages.dev/)。
