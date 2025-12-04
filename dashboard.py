import streamlit as st
import pandas as pd
from analytics import get_vendors_list, get_daily_revenue_df, get_product_revenue_for_date

# Можем по желание да сложим и map от vendor_id към име
VENDOR_NAMES = {
    192: "WhiteMe",
    419: "AirWays",
    # тук можеш да добавяш още, когато ги имаш
}

def main():
    st.set_page_config(page_title="BigArena Vendor Dashboard", layout="wide")

    st.title("📊 BigArena Vendor Dashboard")

    # 1. Избор на vendor
    vendor_ids = get_vendors_list()
    if not vendor_ids:
        st.error("Няма намерени vendor-и в базата (sales/product_prices). Увери се, че има данни.")
        return

    default_vendor = vendor_ids[0]
    vendor_id = st.sidebar.selectbox(
        "Избери vendor",
        options=vendor_ids,
        format_func=lambda vid: f"{VENDOR_NAMES.get(vid, 'Vendor ' + str(vid))} (ID: {vid})",
        index=vendor_ids.index(default_vendor)
    )

    st.sidebar.markdown(f"**Избран vendor ID:** `{vendor_id}`")

    # 2. Дневен оборот (по дни) за избрания vendor
    daily_df = get_daily_revenue_df(vendor_id)

    if daily_df.empty:
        st.warning("Няма записани продажби за този vendor.")
        return

    st.subheader("📅 Оборот по дни")

    # Преобразуваме датата към тип datetime за по-добро форматиране
    daily_df["date"] = pd.to_datetime(daily_df["date"])

    # Показваме графика
    st.line_chart(
        daily_df.set_index("date")["total_revenue"],
        height=300
    )

    # Показваме и таблично
    st.dataframe(
        daily_df.sort_values("date", ascending=False),
        use_container_width=True
    )

    # 3. Детайли по продукти за избран ден
    st.subheader("🔍 Детайлен оборот по продукти за избран ден")

    # Избор на дата от наличните
    unique_dates = daily_df["date"].dt.date.unique()
    selected_date = st.selectbox(
        "Избери дата",
        options=unique_dates,
        format_func=lambda d: d.strftime("%Y-%m-%d")
    )
    selected_date_str = selected_date.strftime("%Y-%m-%d")

    product_df = get_product_revenue_for_date(vendor_id, selected_date_str)

    total_revenue_for_day = product_df["revenue"].sum() if not product_df.empty else 0.0

    st.markdown(
        f"**Общ оборот за {selected_date_str}:** {total_revenue_for_day:.2f} лв."
    )

    if product_df.empty:
        st.info("Няма продажби за този ден.")
    else:
        st.dataframe(
            product_df,
            use_container_width=True
        )

if __name__ == "__main__":
    main()
