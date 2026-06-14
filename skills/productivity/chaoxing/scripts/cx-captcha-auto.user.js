// ==UserScript==
// @name         超星滑块验证码全自动过
// @namespace    chaoxing-agent-skill
// @version      1.0
// @description  拦截CAPTCHA → Capsolver算距离 → 直接调验证API → 全自动进考场
// @author       chaoxing-agent-skill
// @match        *://*/exam/test/examcode/examnotes*
// @grant        GM_xmlhttpRequest
// @grant        unsafeWindow
// @run-at       document-start
// ==/UserScript==

(function() {
    'use strict';

    // ═══════════════════════════════════════════════════════════
    // 配置：把 YOUR_CAPSOLVER_KEY 替换为你的 Capsolver API Key
    // 注册: https://dashboard.capsolver.com
    // ═══════════════════════════════════════════════════════════
    const CAPS_KEY = 'YOUR_CAPSOLVER_KEY';
    const CAPTCHA_API = 'https://captcha.chaoxing.com';

    let captchaId = null, captchaToken = null, captchaCallback = null;
    let bgUrl = null, smUrl = null;

    function log(msg) { console.log('[CX-CAPTCHA]', msg); }

    function uuid() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
            const r = Math.random() * 16 | 0;
            return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
        });
    }

    function downloadImage(url) {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'GET', url: url, responseType: 'blob',
                headers: {
                    'User-Agent': navigator.userAgent,
                    'Referer': 'https://mooc1.chaoxing.com/'
                },
                onload(r) {
                    if (r.status !== 200) return reject(new Error('HTTP ' + r.status));
                    const reader = new FileReader();
                    reader.onload = () => resolve(reader.result.split(',')[1]);
                    reader.onerror = reject;
                    reader.readAsDataURL(r.response);
                },
                onerror: reject
            });
        });
    }

    async function getCapsolverDistance(bgB64, smB64) {
        const resp = await fetch('https://api.capsolver.com/createTask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                clientKey: CAPS_KEY,
                task: {
                    type: 'VisionEngine',
                    module: 'slider_1',
                    image: smB64,
                    imageBackground: bgB64,
                    websiteURL: 'https://mooc1.chaoxing.com'
                }
            })
        });
        const data = await resp.json();
        if (data.errorId === 0 && data.status === 'ready') {
            return data.solution.distance;
        }
        log('Capsolver error: ' + JSON.stringify(data));
        return null;
    }

    async function solveCaptcha() {
        // Step 1: Get server time
        const confResp = await fetch(
            `${CAPTCHA_API}/captcha/get/conf?callback=cx_captcha_function&captchaId=${captchaId}&_=${Date.now()}`
        );
        const confText = await confResp.text();
        const conf = JSON.parse(confText.match(/\(([\s\S]*)\)/)[1]);
        const serverTime = conf.t;

        // Step 2: Get image token + URLs
        const rn = Math.floor(100000 + Math.random() * 900000);
        const ck = md5('' + serverTime + rn);
        const tok = md5('' + serverTime + captchaId + 'slide' + ck) + ':' + (serverTime + 300000);
        const iv = uuid();

        const imgResp = await fetch(
            `${CAPTCHA_API}/captcha/get/verification/image?callback=cx_captcha_function` +
            `&captchaId=${captchaId}&type=slide&version=1.1.20` +
            `&captchaKey=${ck}&token=${tok}` +
            `&referer=https://mooc1.chaoxing.com&iv=${iv}&_=${Date.now()}`
        );
        const imgText = await imgResp.text();
        const imgData = JSON.parse(imgText.match(/\(([\s\S]*)\)/)[1]);
        const imageToken = imgData.token;
        const bgUrl = imgData.imageVerificationVo.shadeImage;
        const smUrl = imgData.imageVerificationVo.cutoutImage;

        // Step 3: Download images
        log('Downloading CAPTCHA images...');
        const bgB64 = await downloadImage(bgUrl);
        const smB64 = await downloadImage(smUrl);

        // Step 4: Capsolver
        log('Solving with Capsolver...');
        const distance = await getCapsolverDistance(bgB64, smB64);
        if (distance === null) {
            log('Capsolver failed — falling back to manual slider');
            return false;
        }
        log('Capsolver distance: ' + distance);

        // Step 5: Verify with 超星 API
        const clickArr = JSON.stringify([{ x: distance }]);
        const verifyResp = await fetch(
            `${CAPTCHA_API}/captcha/check/verification/result?callback=cx_captcha_function` +
            `&captchaId=${captchaId}&type=slide&token=${imageToken}` +
            `&textClickArr=${encodeURIComponent(clickArr)}&coordinate=[]` +
            `&runEnv=10&version=1.1.20&t=a&iv=${uuid()}&_=${Date.now()}`
        );
        const verifyText = await verifyResp.text();
        const verifyData = JSON.parse(verifyText.match(/\(([\s\S]*)\)/)[1]);

        if (!verifyData.result) {
            log('Verify failed: ' + JSON.stringify(verifyData));
            return false;
        }

        const extra = JSON.parse(verifyData.extraData || '{}');
        const validate = extra.validate || '';
        log('Validate token: ' + validate.substring(0, 20) + '...');

        // Step 6: Inject into page
        const pageWindow = unsafeWindow;
        const doc = document;

        // Wait for DOM to be ready
        const inject = () => {
            const captchaValidate = doc.querySelector('#captchavalidate');
            const captchaCheck = doc.querySelector('#captchaCheck');
            const examCheck = doc.querySelector('#examCheck');

            if (!captchaValidate || !captchaCheck) {
                setTimeout(inject, 200);
                return;
            }

            captchaValidate.value = validate;
            captchaCheck.value = '0';
            if (examCheck) examCheck.value = '0';

            // Hijack showCXCaptcha to skip slider UI
            const origSC = pageWindow.showCXCaptcha;
            pageWindow.showCXCaptcha = function(cb) {
                if (typeof cb === 'function') cb();
            };

            // Trigger exam entry
            log('Triggering jumpExam...');
            if (typeof pageWindow.jumpExam === 'function') {
                pageWindow.jumpExam('true');
            }

            // Restore original after a delay
            setTimeout(() => {
                pageWindow.showCXCaptcha = origSC;
            }, 2000);
        };

        inject();
        return true;
    }

    // MD5 implementation (for CAPTCHA auth token)
    function md5(string) {
        function md5cycle(x, k) {
            var a = x[0], b = x[1], c = x[2], d = x[3];
            a = ff(a, b, c, d, k[0], 7, -680876936);
            d = ff(d, a, b, c, k[1], 12, -389564586);
            c = ff(c, d, a, b, k[2], 17, 606105819);
            b = ff(b, c, d, a, k[3], 22, -1044525330);
            a = ff(a, b, c, d, k[4], 7, -176418897);
            d = ff(d, a, b, c, k[5], 12, 1200080426);
            c = ff(c, d, a, b, k[6], 17, -1473231341);
            b = ff(b, c, d, a, k[7], 22, -45705983);
            a = ff(a, b, c, d, k[8], 7, 1770035416);
            d = ff(d, a, b, c, k[9], 12, -1958414417);
            c = ff(c, d, a, b, k[10], 17, -42063);
            b = ff(b, c, d, a, k[11], 22, -1990404162);
            a = ff(a, b, c, d, k[12], 7, 1804603682);
            d = ff(d, a, b, c, k[13], 12, -40341101);
            c = ff(c, d, a, b, k[14], 17, -1502002290);
            b = ff(b, c, d, a, k[15], 22, 1236535329);
            a = gg(a, b, c, d, k[1], 5, -165796510);
            d = gg(d, a, b, c, k[6], 9, -1069501632);
            c = gg(c, d, a, b, k[11], 14, 643717713);
            b = gg(b, c, d, a, k[0], 20, -373897302);
            a = gg(a, b, c, d, k[5], 5, -701558691);
            d = gg(d, a, b, c, k[10], 9, 38016083);
            c = gg(c, d, a, b, k[15], 14, -660478335);
            b = gg(b, c, d, a, k[4], 20, -405537848);
            a = gg(a, b, c, d, k[9], 5, 568446438);
            d = gg(d, a, b, c, k[14], 9, -1019803690);
            c = gg(c, d, a, b, k[3], 14, -187363961);
            b = gg(b, c, d, a, k[8], 20, 1163531501);
            a = gg(a, b, c, d, k[13], 5, -1444681467);
            d = gg(d, a, b, c, k[2], 9, -51403784);
            c = gg(c, d, a, b, k[7], 14, 1735328473);
            b = gg(b, c, d, a, k[12], 20, -1926607734);
            a = hh(a, b, c, d, k[5], 4, -378558);
            d = hh(d, a, b, c, k[8], 11, -2022574463);
            c = hh(c, d, a, b, k[11], 16, 1839030562);
            b = hh(b, c, d, a, k[14], 23, -35309556);
            a = hh(a, b, c, d, k[1], 4, -1530992060);
            d = hh(d, a, b, c, k[4], 11, 1272893353);
            c = hh(c, d, a, b, k[7], 16, -155497632);
            b = hh(b, c, d, a, k[10], 23, -1094730640);
            a = hh(a, b, c, d, k[13], 4, 681279174);
            d = hh(d, a, b, c, k[0], 11, -358537222);
            c = hh(c, d, a, b, k[3], 16, -722521979);
            b = hh(b, c, d, a, k[6], 23, 76029189);
            a = hh(a, b, c, d, k[9], 4, -640364487);
            d = hh(d, a, b, c, k[12], 11, -421815835);
            c = hh(c, d, a, b, k[15], 16, 530742520);
            b = hh(b, c, d, a, k[2], 23, -995338651);
            a = ii(a, b, c, d, k[0], 6, -198630844);
            d = ii(d, a, b, c, k[7], 10, 1126891415);
            c = ii(c, d, a, b, k[14], 15, -1416354905);
            b = ii(b, c, d, a, k[5], 21, -57434055);
            a = ii(a, b, c, d, k[12], 6, 1700485571);
            d = ii(d, a, b, c, k[3], 10, -1894986606);
            c = ii(c, d, a, b, k[10], 15, -1051523);
            b = ii(b, c, d, a, k[1], 21, -2054922799);
            a = ii(a, b, c, d, k[8], 6, 1873313359);
            d = ii(d, a, b, c, k[15], 10, -30611744);
            c = ii(c, d, a, b, k[6], 15, -1560198380);
            b = ii(b, c, d, a, k[13], 21, 1309151649);
            a = ii(a, b, c, d, k[4], 6, -145523070);
            d = ii(d, a, b, c, k[11], 10, -1120210379);
            c = ii(c, d, a, b, k[2], 15, 718787259);
            b = ii(b, c, d, a, k[9], 21, -343485551);
            x[0] = add32(a, x[0]);
            x[1] = add32(b, x[1]);
            x[2] = add32(c, x[2]);
            x[3] = add32(d, x[3]);
        }
        function cmn(q, a, b, x, s, t) {
            a = add32(add32(a, q), add32(x, t));
            return add32((a << s) | (a >>> (32 - s)), b);
        }
        function ff(a, b, c, d, x, s, t) { return cmn((b & c) | ((~b) & d), a, b, x, s, t); }
        function gg(a, b, c, d, x, s, t) { return cmn((b & d) | (c & (~d)), a, b, x, s, t); }
        function hh(a, b, c, d, x, s, t) { return cmn(b ^ c ^ d, a, b, x, s, t); }
        function ii(a, b, c, d, x, s, t) { return cmn(c ^ (b | (~d)), a, b, x, s, t); }
        function md5blk(s) {
            var md5blks = [], i;
            for (i = 0; i < 64; i += 4) {
                md5blks[i>>2] = s.charCodeAt(i)
                    + (s.charCodeAt(i+1) << 8)
                    + (s.charCodeAt(i+2) << 16)
                    + (s.charCodeAt(i+3) << 24);
            }
            return md5blks;
        }
        function md5blk_array(a) {
            var md5blks = [], i;
            for (i = 0; i < 64; i += 4) {
                md5blks[i>>2] = a[i]
                    + (a[i+1] << 8)
                    + (a[i+2] << 16)
                    + (a[i+3] << 24);
            }
            return md5blks;
        }
        function md51(s) {
            var n = s.length, state = [1732584193, -271733879, -1732584194, 271733878], i;
            for (i = 64; i <= n; i += 64) md5cycle(state, md5blk(s.substring(i - 64, i)));
            s = s.substring(i - 64);
            var tail = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
            for (i = 0; i < s.length; i++) tail[i>>2] |= s.charCodeAt(i) << ((i%4) << 3);
            tail[i>>2] |= 0x80 << ((i%4) << 3);
            if (i > 55) { md5cycle(state, md5blk_array(tail)); for (i = 0; i < 16; i++) tail[i] = 0; }
            tail[14] = n * 8;
            md5cycle(state, tail);
            return state;
        }
        function add32(a, b) { return (a + b) & 0xFFFFFFFF; }
        function hex_chr(n) { var h = '0123456789abcdef'.split(''); return h[(n >> 4) & 0xF] + h[n & 0xF]; }
        function rhex(n) { var s = '', j = 0; for (; j < 4; j++) s += hex_chr((n >> (j * 8 + 4)) & 0x0F) + hex_chr((n >> (j * 8)) & 0x0F); return s; }
        function hex(x) { for (var i = 0; i < x.length; i++) x[i] = rhex(x[i]); return x.join(''); }

        return hex(md51(string));
    }

    // ── Hijack CAPTCHA initialization ──────────────────────────

    const origDefineProperty = Object.defineProperty;
    let hijacked = false;

    // Intercept showCXCaptcha assignment
    Object.defineProperty = function(obj, prop, desc) {
        if (prop === 'showCXCaptcha' && desc.value && !hijacked) {
            hijacked = true;
            const origFn = desc.value;
            desc.value = function(callback) {
                log('CAPTCHA intercepted!');
                captchaCallback = callback;
                captchaId = document.querySelector('#captchaCaptchaId')?.value || '';

                if (CAPS_KEY === 'YOUR_CAPSOLVER_KEY') {
                    log('Capsolver key not configured. Falling back to manual slider.');
                    return origFn.call(this, callback);
                }

                log('Starting auto-solve pipeline...');
                solveCaptcha().then(success => {
                    if (!success) {
                        log('Auto-solve failed. Falling back to manual slider.');
                        origFn.call(this, callback);
                    }
                }).catch(err => {
                    log('Pipeline error: ' + err.message);
                    origFn.call(this, callback);
                });
            };
        }
        return origDefineProperty.call(Object, obj, prop, desc);
    };

    log('Loaded. Waiting for CAPTCHA...');
})();
