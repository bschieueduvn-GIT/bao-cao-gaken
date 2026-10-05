import requests
import schedule
import time
from datetime import datetime, timezone, timedelta

PANCAKE_KEY  = "620bae192ea4da03deead0744a798386"
PANCAKE_SHOP = "1942950885"
BOT_TOKEN    = "8931084156:AAFpFiP89nfgJZuo799fmiCpIAbK3EZMh9U"
CHAT_ID      = "-5590289313"

VN = timezone(timedelta(hours=7))


def chuan_hoa_ten(ten):
    import re
    return re.sub(r"^\d+\s+", "", ten.strip()).strip()


def lay_don_thang():
    now   = datetime.now(VN)
    ngay  = now.day
    thang = now.month
    nam   = now.year

    ket_qua = {}
    trang   = 1

    # Tính đầu tháng và đầu ngày hôm nay theo VN
    dau_thang = datetime(nam, thang, 1, tzinfo=VN)
    hom_nay_dau = datetime(nam, thang, ngay, tzinfo=VN)
    hom_nay_cuoi = datetime(nam, thang, ngay, 23, 59, 59, tzinfo=VN)

    total_pages = 1
    while trang <= total_pages:
        url = (
            f"https://pos.pages.fm/api/v1/shops/{PANCAKE_SHOP}/orders"
            f"?api_key={PANCAKE_KEY}&page_size=200&page_number={trang}"
        )
        try:
            res  = requests.get(url, timeout=30)
            data = res.json()
        except Exception as e:
            print(f"Lỗi API trang {trang}: {e}")
            break

        if not data.get("success") or not data.get("data"):
            break

        total_pages = data.get("total_pages", 1)

        for don in data["data"]:
            if don.get("status") == 0:
                continue
            seller = don.get("assigning_seller")
            if not seller or not seller.get("name"):
                continue

            # Dùng inserted_at để xác định tháng tạo đơn
            tg_str = don.get("inserted_at", "")
            try:
                tg = datetime.fromisoformat(tg_str).replace(tzinfo=timezone.utc).astimezone(VN)
            except Exception:
                continue

            # Chỉ lấy đơn trong tháng hiện tại
            if tg < dau_thang or tg.month != thang or tg.year != nam:
                continue

            ten = chuan_hoa_ten(seller["name"])
            if ten not in ket_qua:
                ket_qua[ten] = {"hom_nay": 0, "cong_don": 0}

            gia = don.get("total_price") or 0
            ket_qua[ten]["cong_don"] += gia
            if hom_nay_dau <= tg <= hom_nay_cuoi:
                ket_qua[ten]["hom_nay"] += gia

        trang += 1

    return ket_qua, ngay, thang, nam


def dinh_dang_tien(so):
    s = f"{so:,}".replace(",", ".")
    return s + " đ"


def tao_tin_nhan(ket_qua, ngay, thang, nam):
    now = datetime.now(VN)
    lines = [
        "📊 *BÁO CÁO DOANH SỐ GAKEN*",
        f"🗓 Ngày {ngay:02d}/{thang:02d}/{nam} — {now.strftime('%H:%M')}",
        "",
    ]

    # Sắp xếp theo cộng dồn giảm dần
    ds = sorted(ket_qua.items(), key=lambda x: x[1]["cong_don"], reverse=True)

    for ten, sl in ds:
        ten_ngan = " ".join(ten.split()[-2:]) if len(ten.split()) > 2 else ten
        lines.append(f"  👤 {ten_ngan}")
        lines.append(f"     Hôm nay:  `{dinh_dang_tien(sl['hom_nay'])}`")
        lines.append(f"     Cộng dồn: `{dinh_dang_tien(sl['cong_don'])}`")

    tong = sum(v["cong_don"] for v in ket_qua.values())
    lines.append("")
    lines.append(f"🏆 *Tổng tháng {thang}: `{dinh_dang_tien(tong)}`*")
    return "\n".join(lines)


def gui_telegram(tin):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": tin, "parse_mode": "Markdown"}, timeout=15)
        if r.status_code == 200:
            print(f"[{datetime.now(VN).strftime('%H:%M:%S')}] Gửi báo cáo OK")
        else:
            print(f"[{datetime.now(VN).strftime('%H:%M:%S')}] Lỗi Telegram: {r.text}")
    except Exception as e:
        print(f"Lỗi gửi Telegram: {e}")


def chay_bao_cao():
    print(f"[{datetime.now(VN).strftime('%H:%M:%S')}] Đang lấy dữ liệu Pancake...")
    try:
        ket_qua, ngay, thang, nam = lay_don_thang()
        if not ket_qua:
            print("Không có đơn nào trong tháng.")
            return
        tin = tao_tin_nhan(ket_qua, ngay, thang, nam)
        gui_telegram(tin)
    except Exception as e:
        print(f"Lỗi: {e}")


schedule.every().day.at("11:30").do(chay_bao_cao)
schedule.every().day.at("16:30").do(chay_bao_cao)

if __name__ == "__main__":
    print("=== Báo cáo doanh số GAKEN đang chạy ===")
    print("Lịch: 11:30 và 16:30 mỗi ngày (giờ VN)")

    # Chạy thử ngay khi khởi động
    chay_bao_cao()

    while True:
        schedule.run_pending()
        time.sleep(30)
