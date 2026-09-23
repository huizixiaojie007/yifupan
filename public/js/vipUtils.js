/**
 * 会员（VIP）功能守卫工具
 * 数据来源：localStorage 的 user_info（登录时由 login.html 写入）
 * 有效会员条件：is_vip 为 true 且 vip_date 大于当前日期
 * 用法：window.VipGuard.isValidVip() 判断；window.VipGuard.guard('功能名') 校验+提示，返回布尔值
 */
(function () {
    // 读取用户信息（跨iframe同源共享localStorage）
    function getVipInfo() {
        try {
            const raw = localStorage.getItem('user_info');
            if (!raw) return null;
            return JSON.parse(raw);
        } catch (e) {
            return null;
        }
    }

    // 是否有效会员：is_vip 为 true 且 vip_date 大于当前日期
    function isValidVip() {
        const info = getVipInfo();
        if (!info || info.is_vip !== true) return false;
        if (!info.vip_date) return false;
        // 按本地日期比较（vip_date格式YYYY-MM-DD），严格大于当前日期才有效
        const vipDate = new Date(String(info.vip_date).slice(0, 10) + 'T00:00:00');
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return vipDate > today;
    }

    // 功能守卫：非有效会员时弹出提示并返回 false（调用方据此中断功能）
    function guard(featureName) {
        if (isValidVip()) return true;
        const info = getVipInfo();
        let msg;
        if (info && info.is_vip === true && info.vip_date) {
            msg = `「${featureName}」为会员专享功能，您的会员已于 ${String(info.vip_date).slice(0, 10)} 到期，请续费后再使用`;
        } else {
            msg = `「${featureName}」为会员专享功能，请开通会员后再使用`;
        }
        alert(msg);
        return false;
    }

    window.VipGuard = { getVipInfo, isValidVip, guard };
})();
