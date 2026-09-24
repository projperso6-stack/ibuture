import env from './env.js?v=1788169639933';

class SealSubscribePlugin {
  constructor(el) {
    this.timer = null;
  }
  updateSellingPlan() {
    const input = document.querySelector('[data-sls-selling_plan]');
    if (input) {
      this.handle(input);
    }
  }
  handle(slsElementInput) {
    const id = Number.parseInt(slsElementInput.value, 10);
    this.updatePoints(id);
  }
  updatePoints(value) {
    window.__POINTS.sellingPlanID = value;
    window.__POINTS.reloadProductPage();
  }
}

// Plugins
function registerPlugins() {
  const slsPlugin = new SealSubscribePlugin();
  return {
    slsPlugin
  };
}
// Main

((global) => {
  function Points() {
    // 版本，仅用于前端线上代码版本的识别
    this.VERSION = '0.06121801beta';
    this.SHOPIFY_ROOT = window.Shopify?.routes.root || '/';
    //店铺id
    this.SHOP_ID = 0;
    // 店铺域名
    this.SHOP_DOMAIN = '';
    // 用户id
    this.CUSTOMER_ID = 0;
    // 最外层元素
    this.OUTER_DOM = document.querySelector('.bm_top_product_div');
    //产品积分span dom元素
    this.PRODUCT_POINTS_DOM = document.querySelector('.bm_product_points');
    //span值
    this.spanTextValue = JSON.parse(
      document.querySelector('#bm_product_span_value')?.textContent || 'null'
    );
    // 当前产品id
    this.PRODUCT_ID = 0;
    //变体数组
    this.VARIANTS_ARRAY = [];
    //当前变体
    this.CURRENT_VARIANTS = {};
    //用户卸载或状态未开启标志位,初始状态开启
    this.SHOW_LABEL = true;
    // 验证产品系列接口标识
    this.IS_AUTH_COLLECTION = false;
    // 定制价格扣除 GST 的商家
    this.EXCLUSION_GST_SHOP_MAP = {
      'efc517-eb.myshopify.com': 0.15,
      '6fecd6-fc.myshopify.com': 0.1
    };
    //营销事件翻倍数
    this.pointsMultiples = 0;
    // 当前place an order 规则使用的产品系列
    this.ruleCollections = [];
    //获得积分类型 1 按比例赠送积分 | 2 固定送积分
    this.earnType = 1;
    //每积分的金额
    this.amount = 0;
    //赠送积分
    this.presentPoints = 0;
    //当前变体购买后赠送的总积分
    this.points = 0;
    //当前变体价格
    this.variantPrice = 0;
    //定时任务清空缓存
    this.setTimeoutHandle = null;
    // variants.selling_plan_allocations.selling_plan_id
    this.sellingPlanID = 0;
    this.lastSellingPlanID = 0;
    //初始化
    this.init();
  }

  Points.prototype = {
    constructor: Points,

    _cache: {
      getPointsStatus: {}
    },

    init: function () {
      // 获取当前无参数的域名，后缀加js，获取产品数据
      const url = window.location.origin + window.location.pathname + '.js';
      fetch(url)
        .then((response) => response.json())
        .then((json) => {
          //变体数组
          this.VARIANTS_ARRAY = json.variants;
          //当前变体
          this.CURRENT_VARIANTS = this.VARIANTS_ARRAY[0];
          //当前变体价格
          this.variantPrice = (this.getVariantPrice(this.CURRENT_VARIANTS) || 0) / 100;
          // 获取产品id
          this.initSetting();
        });
    },

    initSetting: function () {
      // 店铺ID
      this.SHOP_ID = window.__st.a;
      this.SHOP_DOMAIN = window.Shopify.shop;
      this.PRODUCT_ID = window.__st.rid || 0;
      // 用户 id
      this.CUSTOMER_ID = window.__st.cid || 0;
      //获取积分配置
      this.getPointsStatus();
    },

    getPointsStatus: function () {
      const that = this;
      async function afterFetch(resData) {
        // 用户已卸载或用户不开启按钮
        if (
          resData.is_delete == 1 ||
          resData.points_status != 1 ||
          resData.point_rule_status != 1 ||
          resData.member_state == 2
        ) {
          that.SHOW_LABEL = false;
          that.hideLabel();
          return;
        }

        if (that.SHOW_LABEL) {
          that.pointsMultiples = resData.points_multiples;
          that.amount = resData.amount;
          that.presentPoints = resData.present_points;
          that.earnType = resData.earn_type;
          that.ruleCollections = resData.collections;
          if (!that.IS_AUTH_COLLECTION) {
            that.SHOW_LABEL = await that.checkProductRange(resData.apply_to);
            that.IS_AUTH_COLLECTION = true;
          }
          if (!that.SHOW_LABEL) {
            that.hideLabel();
            return;
          }
          that.createPointsDom();
        }
      }

      const uniqKey = '' + this.SHOP_ID + that.CURRENT_VARIANTS?.id;
      if (that._cache.getPointsStatus[uniqKey]) {
        afterFetch(this._cache.getPointsStatus[uniqKey]);
        return;
      }

      if (!that.SHOW_LABEL) return;

      that.ajax({
        url: `${env.API_BASE_STOREFRONT_URL}points/label`,
        contentType: 'application/json',
        data: {
          variantId: that.CURRENT_VARIANTS.id
        },
        success: (res) => {
          if (res.code == 200 && res.data != null) {
            const resData = res.data;
            that._cache.getPointsStatus[uniqKey] = resData;
            afterFetch(resData);
          }
        },
        error: (XMLHttpRequest, textStatus, errorThrown) => {}
      });
    },

    // 检查该商品是否在该规则使用范围内（1-所有产品，2-产品系列，产品id，(?.变体)）
    checkProductRange: async function (range) {
      if (range === 1) {
        return true;
      }
      if (range === 2) {
        return await this.checkCollectionsValid();
      }
    },

    // 检查商品是否属于规则集合
    checkCollectionsValid: async function () {
      // const { collections } = await this.getCollectionJSON();
      // if (collections.length === 0) return false;
      // if (!this.ruleCollectionValid(collections)) return false;

      const { data } = await this.checkProductAppliedToRule();
      return data.in_collection === 1;
    },

    // 检查当前规则应用的产品系列是否有效
    ruleCollectionValid(collections) {
      const allCollectionIds = collections.map((item) => item.id);
      return this.ruleCollections.some((ruleCollection) =>
        allCollectionIds.includes(ruleCollection)
      );
    },

    // 查询该商品是否属于当前规则应用范围内
    checkProductAppliedToRule: async function () {
      const params = {
        product_ids: [this.PRODUCT_ID],
        collection_ids: this.ruleCollections
      };
      const options = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(params)
      };

      const response = await fetch(env.API_BASE_URL + 'inCollection', options);
      return response.json();
    },

    // 获取collection.json
    getCollectionJSON: async function () {
      const response = await fetch(this.SHOPIFY_ROOT + 'collections.json');
      return response.json();
    },

    createPointsDom: function () {
      //计算当前变体购买后获得积分
      if (this.earnType == 2) {
        this.points =
          this.pointsMultiples !== 0
            ? Math.floor(this.presentPoints * this.pointsMultiples)
            : this.presentPoints;
      } else {
        let calcPointsUnit = Math.floor(this.variantPrice / this.amount);
        const shopGSTPercent = this.EXCLUSION_GST_SHOP_MAP[this.SHOP_DOMAIN];
        if (shopGSTPercent) {
          const gstRate = (1 + shopGSTPercent) * 100;
          const excludeGSTPrice = Math.floor((this.variantPrice * 100) / gstRate);
          calcPointsUnit = Math.floor(excludeGSTPrice / this.amount);
        }

        this.points =
          this.pointsMultiples !== 0
            ? Math.floor(calcPointsUnit * this.presentPoints * this.pointsMultiples)
            : Math.floor(calcPointsUnit * this.presentPoints);
      }

      if (this.points <= 0) {
        this.hideLabel();
      }

      // 插入积分label
      this.PRODUCT_POINTS_DOM.textContent = this.spanTextValue?.replace('{Points}', this.points);

      this.PRODUCT_POINTS_DOM.onclick = () => {
        if (!window.__BooM) {
          return;
        }
        // C-widget
        const BoomDom = window.__BooM;
        if (BoomDom.LAUNCHER_STATE == 1) {
          BoomDom.startBtn.onclick();
        }
      };
    },

    // 隐藏label 解决外层盒子占位问题
    hideLabel: function () {
      // 若不属于该规则应用范围则不展示label
      this.OUTER_DOM.style.display = 'none';
    },

    // ajax方法封装
    ajax: (options) => {
      options = options || {};
      options.type = (options.type || 'POST').toUpperCase();
      options.dataType = options.dataType || 'json';
      options.timeout = options.timeout || 5000;
      options.contentType = options.contentType || 'application/x-www-form-urlencoded';
      var params = formatParams(options.data);
      var xhr;
      if (window.XMLHttpRequest) {
        xhr = new XMLHttpRequest();
      } else if (window.ActiveObject) {
        xhr = new ActiveXobject('Microsoft.XMLHTTP');
      }
      if (options.type == 'GET') {
        xhr.open('GET', options.url + '?' + params, true);
        xhr.responseType = options.dataType;
        xhr.send(null);
      } else if (options.type == 'POST') {
        xhr.open('post', options.url, true);
        xhr.responseType = options.dataType;
        xhr.setRequestHeader('Content-type', options.contentType);
        xhr.send(options.contentType == 'application/json' ? JSON.stringify(options.data) : params);
      }
      setTimeout(() => {
        if (xhr.readySate != 4) {
          xhr.abort();
        }
      }, options.timeout);
      xhr.onreadystatechange = () => {
        if (xhr.readyState == 4) {
          var status = xhr.status;
          if ((status >= 200 && status < 300) || status == 304) {
            options.success && options.success(xhr.response);
          } else {
            options.error && options.error(status);
          }
        }
      };
      function formatParams(data) {
        var arr = [];
        for (var name in data) {
          arr.push(encodeURIComponent(name) + '=' + encodeURIComponent(data[name]));
        }
        arr.push(('v=' + Math.random()).replace('.', ''));
        return arr.join('&');
      }
    },

    reloadProductPage: function () {
      if (location.href.indexOf('variant=') !== -1) {
        const window_variant_id = Number(location.href.split('variant=')[1]);
        if (
          this.CURRENT_VARIANTS?.id !== window_variant_id ||
          this.sellingPlanID !== this.lastSellingPlanID
        ) {
          this.lastSellingPlanID = this.sellingPlanID;

          for (let i = 0; i < this.VARIANTS_ARRAY.length; i++) {
            if (this.VARIANTS_ARRAY[i].id == window_variant_id) {
              this.CURRENT_VARIANTS = this.VARIANTS_ARRAY[i];
              this.variantPrice = (this.getVariantPrice(this.CURRENT_VARIANTS) || 0) / 100;
              this.getPointsStatus();
              break;
            }
          }
        }
      }
    },

    getVariantPrice: function (variant) {
      if (!this.sellingPlanID) {
        return variant.price;
      }
      const sellingPlan = variant.selling_plan_allocations.find(
        (item) => item.selling_plan_id === this.sellingPlanID
      );
      return sellingPlan?.price || variant.price;
    }
  };

  // 判断是否已经挂载了label
  if (!window.__POINTS) {
    window.__POINTS = new Points();
  } else {
    return;
  }

  const { slsPlugin } = registerPlugins();
  // 监视DOM结构，重新计算lable积分
  (function watchDOM() {
    // let previousUrl = window.location.href;
    const observer = new MutationObserver(
      throttle((mutations) => {
        slsPlugin.updateSellingPlan();
        // render
        window.__POINTS.reloadProductPage();
      }, 100)
    );
    const config = { subtree: true, childList: true };
    observer.observe(document, config);
  })();
})(window);

// utils
function throttle(callback, time) {
  let timer = null;
  return function (...args) {
    if (timer) return;
    timer = setTimeout(() => {
      callback.call(this, args);
      timer = null;
    }, time);
  };
}
