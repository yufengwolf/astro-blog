# 太阳系 3D 模型

下面是通过 `iframe` 嵌入的太阳系 3D 交互站**主页**（导航卡片）。首页列出「太阳系总览 / 地月 / 火星 / 木星 / 土星 / 天王星 / 海王星 / 冥王星」八个系统，**点击任意卡片即可在下方窗口内直接打开对应系统**，无需离开本页。点右上角「全屏」可铺满屏幕查看；手机端全屏建议横屏。

<div class="solar-embed" id="solar-embed" data-home-src="https://astro-solar-3d.pages.dev/">
  <div class="solar-bar">
    <span class="solar-title">太阳系 3D 交互站</span>
    <span class="solar-bar-btns">
      <button type="button" class="solar-home-btn" id="solar-home-btn">↺ 重新选择</button>
      <button type="button" class="solar-fs-btn" id="solar-fs-btn">全屏</button>
    </span>
  </div>
  <div class="solar-frame">
    <iframe src="https://astro-solar-3d.pages.dev/" title="太阳系 3D 交互站" loading="lazy" allowfullscreen allow="fullscreen"></iframe>
    <div class="solar-rotate">
      <span class="solar-rotate-icon">↻</span>
      请旋转手机至横屏，获得更大的观测视野
    </div>
  </div>
</div>

- 进入某个系统后，点上方「↺ 重新选择」可退回主页换另一个系统看。
- 鼠标拖拽旋转视角，滚轮缩放；悬停天体有白色描边，点击相机飞近并弹出资料卡。
- 右上角面板可调节公转 / 自转速度、太阳亮度，以及「视觉放大 ×N」让小卫星清晰可见。
- 想更大？点「全屏」按钮，再点一次或按 Esc 退出。

如果上面的窗口没有显示，可直接打开 [astro-solar-3d.pages.dev](https://astro-solar-3d.pages.dev/)。
