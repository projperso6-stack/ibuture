
    (function() {
      var preconnectOrigins = ["https://cdn.shopify.com"];
      var scripts = ["/cdn/shopifycloud/checkout-web/assets/c1/polyfills-legacy.uV-pN8XV.js","/cdn/shopifycloud/checkout-web/assets/c1/app-legacy.DGFTmwj-.js","/cdn/shopifycloud/checkout-web/assets/c1/esnext-vendor-legacy.CerKYpGQ.js","/cdn/shopifycloud/checkout-web/assets/c1/context-browser-legacy.Dax1S4Kd.js","/cdn/shopifycloud/checkout-web/assets/c1/checkout-policy-legacy.CmiePcp1.js","/cdn/shopifycloud/checkout-web/assets/c1/receipt-mapper-load-recovery-legacy.BoNprtKM.js","/cdn/shopifycloud/checkout-web/assets/c1/receipt-eager-mappers-legacy.D1jo1Dsv.js","/cdn/shopifycloud/checkout-web/assets/c1/helpers-setAddressErrors-legacy.bc23qytd.js","/cdn/shopifycloud/checkout-web/assets/c1/types-ShopPayInstallments-legacy.CccuUwgb.js","/cdn/shopifycloud/checkout-web/assets/c1/sections-shared-legacy.CuZwXCGD.js","/cdn/shopifycloud/checkout-web/assets/c1/consent-manager-shared-legacy.CH08LyZV.js","/cdn/shopifycloud/checkout-web/assets/c1/error-logger-report-graphql-error-legacy.BccKkaOH.js","/cdn/shopifycloud/checkout-web/assets/c1/cvv-cvvBridge-legacy.BxZ70THn.js","/cdn/shopifycloud/checkout-web/assets/c1/shop-pay-normalizeBuyerDetails-legacy.KwIwwRfR.js","/cdn/shopifycloud/checkout-web/assets/c1/utilities-shopCashMoney-legacy.ds05Vw2q.js","/cdn/shopifycloud/checkout-web/assets/c1/color-contrast-colorContrast-legacy.DDtiD5-Y.js","/cdn/shopifycloud/checkout-web/assets/c1/graphql-redeemable-legacy.ByH8OiOb.js","/cdn/shopifycloud/checkout-web/assets/c1/hydrate-legacy.BPZevWru.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useShopPayExternalAppContext-legacy.DjIHj2h-.js","/cdn/shopifycloud/checkout-web/assets/c1/locale-en-legacy.B5dmqlSW.js","/cdn/shopifycloud/checkout-web/assets/c1/OnePage-legacy.BvZG5hxW.js","/cdn/shopifycloud/checkout-web/assets/c1/components-DeliveryTransition-legacy.CPq84w0G.js","/cdn/shopifycloud/checkout-web/assets/c1/useShopPayButtonClassName-legacy.C-BrGHoi.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useSuppressShopPayModalOnLoad-legacy.BWh2tPRb.js","/cdn/shopifycloud/checkout-web/assets/c1/cross-border-hooks-legacy.Dr-yOUZN.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-usePickupPoints-legacy.C0Jjr1bB.js","/cdn/shopifycloud/checkout-web/assets/c1/ChangeCompanyLocationLink-legacy.mKBMzAdG.js","/cdn/shopifycloud/checkout-web/assets/c1/BillingAddressForm-legacy.BQEwdQXu.js","/cdn/shopifycloud/checkout-web/assets/c1/PhoneField-legacy.DcR4q7Rt.js","/cdn/shopifycloud/checkout-web/assets/c1/ImpressionEventCapture-legacy.8ba5gzVZ.js","/cdn/shopifycloud/checkout-web/assets/c1/components-RedirectionNotice.module-legacy.B7vyQI4b.js","/cdn/shopifycloud/checkout-web/assets/c1/Choice-legacy.BdFNSaJq.js","/cdn/shopifycloud/checkout-web/assets/c1/Checkbox-legacy.CFBOqBXv.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useCanChangeCompanyLocation-legacy.8LyuRFkw.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useForceShopPayUrl-legacy.DHRHNmVh.js","/cdn/shopifycloud/checkout-web/assets/c1/CaptureEvents-ButtonWithRegisterWebPixel-legacy.DQb12gRZ.js","/cdn/shopifycloud/checkout-web/assets/c1/ShopPayLogo-legacy.DvYr4x07.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useWalletsTimeout-legacy.C_ZD7kPw.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-usePostPurchase-legacy.MVuEBXZZ.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useWalletsMonorailTrack-legacy.CNnJ1GNN.js","/cdn/shopifycloud/checkout-web/assets/c1/IncentiveBadge-legacy.nmmIBvwN.js","/cdn/shopifycloud/checkout-web/assets/c1/AutocompleteField-hooks-legacy.BFwCLIWt.js","/cdn/shopifycloud/checkout-web/assets/c1/PendingShipping-legacy.BrMm4xKz.js","/cdn/shopifycloud/checkout-web/assets/c1/useAddressMutationsWithNegotiation-legacy.IoAV9xyY.js","/cdn/shopifycloud/checkout-web/assets/c1/PaymentIcon-legacy.NudZhrUB.js","/cdn/shopifycloud/checkout-web/assets/c1/PaymentLine-legacy.Bj_k1NaG.js","/cdn/shopifycloud/checkout-web/assets/c1/Theme-ThemeOverride-legacy.B2AEIUPo.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useUpdateCheckoutAddress-legacy.LMkulywi.js","/cdn/shopifycloud/checkout-web/assets/c1/payment-usePaymentExemptionReason-legacy.BvjK7sok.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useShopPayProgressIntercepts-legacy.CroLojoI.js","/cdn/shopifycloud/checkout-web/assets/c1/Section-legacy.BERUZ4oK.js","/cdn/shopifycloud/checkout-web/assets/c1/Section-SectionStyleOverride-legacy.s5cNEIZ4.js","/cdn/shopifycloud/checkout-web/assets/c1/utilities-previous-legacy.Dt5HCxh0.js","/cdn/shopifycloud/checkout-web/assets/c1/PaymentErrorBanner-legacy.vvOwLnOg.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useGeneralPaymentErrorMessage-legacy.D246sHib.js","/cdn/shopifycloud/checkout-web/assets/c1/StickyPayButton-StickyPayButton.module-legacy.Dkyx-3O9.js","/cdn/shopifycloud/checkout-web/assets/c1/PayButton-helpers-legacy.BIn6ZX7Z.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-payment-button-legacy.DkaPykOV.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-usePreselectSpi-legacy.DjJQHpCt.js","/cdn/shopifycloud/checkout-web/assets/c1/Switch-legacy.zTXY6PTV.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useAvailableShopPromotionDiscounts-legacy.BkHKNZCT.js","/cdn/shopifycloud/checkout-web/assets/c1/checkout-as-guest-amazon-pay-legacy.BkaB9C4p.js","/cdn/shopifycloud/checkout-web/assets/c1/Middot-legacy.q63taJ-b.js","/cdn/shopifycloud/checkout-web/assets/c1/EstimatedDeliveryContent-legacy.CHcwvzp0.js","/cdn/shopifycloud/checkout-web/assets/c1/ShippingMethodRateLabel-legacy.D4qa0nmU.js","/cdn/shopifycloud/checkout-web/assets/c1/shipping-methods-consolidated-included-legacy.BF_O5qn0.js","/cdn/shopifycloud/checkout-web/assets/c1/ShippingLines-legacy.9K5iPefw.js","/cdn/shopifycloud/checkout-web/assets/c1/ShipmentBreakdown-legacy.B2j8_q8r.js","/cdn/shopifycloud/checkout-web/assets/c1/MerchandiseModal-legacy.CBsv-4Q1.js","/cdn/shopifycloud/checkout-web/assets/c1/ShippingMethodSelector-legacy.BEeNng6S.js","/cdn/shopifycloud/checkout-web/assets/c1/TextArea-legacy.DtYSXMmp.js","/cdn/shopifycloud/checkout-web/assets/c1/SubscriptionPriceBreakdown-legacy.65_exLae.js","/cdn/shopifycloud/checkout-web/assets/c1/hooks-useShopPayNewSignupLoginExperiment-legacy.BU2p5LcG.js","/cdn/shopifycloud/checkout-web/assets/c1/StockProblems-StockProblemsLineItemList-legacy.sKq1U8g3.js"];
      var styles = [];
      var fontPreconnectUrls = [];
      var fontPrefetchUrls = [];
      var imgPrefetchUrls = ["https://cdn.shopify.com/s/files/1/0621/7462/6047/files/BUTURE-logo-2_79e70106-a2bd-404a-845d-1f1b72647153_x320.png?v=1716780349"];

      function preconnect(url, callback) {
        var link = document.createElement('link');
        link.rel = 'dns-prefetch preconnect';
        link.href = url;
        link.crossOrigin = '';
        link.onload = link.onerror = callback;
        document.head.appendChild(link);
      }

      function preconnectAssets() {
        var resources = preconnectOrigins.concat(fontPreconnectUrls);
        var index = 0;
        (function next() {
          var res = resources[index++];
          if (res) preconnect(res, next);
        })();
      }

      function prefetch(url, as, callback) {
        var link = document.createElement('link');
        if (link.relList.supports('prefetch')) {
          link.rel = 'prefetch';
          link.fetchPriority = 'low';
          link.as = as;
          if (as === 'font') link.type = 'font/woff2';
          link.href = url;
          link.crossOrigin = '';
          link.onload = link.onerror = callback;
          document.head.appendChild(link);
        } else {
          var xhr = new XMLHttpRequest();
          xhr.open('GET', url, true);
          xhr.onloadend = callback;
          xhr.send();
        }
      }

      function prefetchAssets() {
        var resources = [].concat(
          scripts.map(function(url) { return [url, 'script']; }),
          styles.map(function(url) { return [url, 'style']; }),
          fontPrefetchUrls.map(function(url) { return [url, 'font']; }),
          imgPrefetchUrls.map(function(url) { return [url, 'image']; })
        );
        var index = 0;
        function run() {
          var res = resources[index++];
          if (res) prefetch(res[0], res[1], next);
        }
        var next = (self.requestIdleCallback || setTimeout).bind(self, run);
        next();
      }

      function onLoaded() {
        try {
          if (parseFloat(navigator.connection.effectiveType) > 2 && !navigator.connection.saveData) {
            preconnectAssets();
            prefetchAssets();
          }
        } catch (e) {}
      }

      if (document.readyState === 'complete') {
        onLoaded();
      } else {
        addEventListener('load', onLoaded);
      }
    })();
  