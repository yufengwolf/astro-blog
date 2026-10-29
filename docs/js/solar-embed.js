/*
 * 太阳系 / 子系统嵌入页：全屏切换 + 移动端横屏提示
 * 配合 .solar-embed 结构使用，支持同一页面存在多个嵌入块（按 class 遍历）。
 */
(function () {
  'use strict';

  var isMobile = function () {
    return window.matchMedia('(max-width: 768px)').matches;
  };
  var isPortrait = function () {
    return window.matchMedia('(orientation: portrait)').matches;
  };
  var fsElement = function () {
    return document.fullscreenElement || document.webkitFullscreenElement || null;
  };

  function requestFS(el) {
    if (el.requestFullscreen) return el.requestFullscreen();
    if (el.webkitRequestFullscreen) return el.webkitRequestFullscreen();
    return Promise.reject(new Error('no-fullscreen'));
  }
  function exitFS() {
    if (document.exitFullscreen) return document.exitFullscreen();
    if (document.webkitExitFullscreen) return document.webkitExitFullscreen();
    return Promise.reject(new Error('no-fullscreen'));
  }

  function attach(embed) {
    var btn = embed.querySelector('.solar-fs-btn');
    if (!btn) return;

    var showRotate = function (show) {
      embed.classList.toggle('solar-show-rotate', !!show);
    };

    var update = function () {
      var fs = fsElement();
      if (fs && fs !== embed) return; // 当前是另一个嵌入块在全屏
      if (fs) {
        btn.textContent = '退出全屏';
        // 移动端进入全屏后尝试锁定横屏
        if (isMobile() && window.screen && screen.orientation && screen.orientation.lock) {
          screen.orientation.lock('landscape').catch(function () {});
        }
        // 仍竖屏则提示旋转
        showRotate(isMobile() && isPortrait());
      } else {
        btn.textContent = '全屏';
        showRotate(false);
        if (window.screen && screen.orientation && screen.orientation.unlock) {
          screen.orientation.unlock();
        }
      }
    };

    btn.addEventListener('click', function () {
      if (fsElement()) {
        exitFS().catch(function () {});
        return;
      }
      requestFS(embed).catch(function () {
        // iOS Safari 等不支持元素全屏：退而求其次在新标签打开独立页
        var frame = embed.querySelector('iframe');
        if (frame) window.open(frame.getAttribute('src'), '_blank', 'noopener');
      });
    });

    document.addEventListener('fullscreenchange', update);
    document.addEventListener('webkitfullscreenchange', update);
    window.addEventListener('orientationchange', function () {
      if (fsElement() === embed) update();
    });
  }

  function init() {
    var embeds = document.querySelectorAll('.solar-embed');
    for (var i = 0; i < embeds.length; i++) attach(embeds[i]);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
