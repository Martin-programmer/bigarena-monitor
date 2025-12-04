import streamlit as st
import pandas as pd

from analytics import (
    get_vendors_list,
    get_daily_revenue_df,
    get_product_revenue_for_date,
    get_vendor_date_bounds,
    get_vendor_stats_for_period,
    get_top_products_for_period,
    get_all_vendors_revenue_for_period,
)

# Мап по желание от vendor_id -> име
VENDOR_NAMES = {
    192: "WhiteMe",
    419: "AirWays",
    # добавяй тук още, когато ги имаш
}


def format_vendor(vid: int) -> str:
    return f"{VENDOR_NAMES.get(vid, 'Vendor ' + str(vid))} (ID: {vid})"


def main():
    st.set_page_config(page_title="BigArena Vendor Dashboard", layout="wide")

    st.title("📊 BigArena Vendor Dashboard")

    # ===== SIDEBAR: избор на vendor и период =====
    vendor_ids = get_vendors_list()
    if not vendor_ids:
        st.error("Няма намерени vendor-и в базата (sales/product_prices). Увери се, че има данни.")
        return

    default_vendor = vendor_ids[0]
    vendor_id = st.sidebar.selectbox(
        "Избери vendor",
        options=vendor_ids,
        format_func=format_vendor,
        index=vendor_ids.index(default_vendor),
    )

    st.sidebar.markdown(f"**Избран vendor ID:** `{vendor_id}`")

    # Граници на датите за избрания vendor
    min_date_str, max_date_str = get_vendor_date_bounds(vendor_id)
    if not min_date_str or not max_date_str:
        st.warning("Няма записани продажби за този vendor.")
        return

    min_date = pd.to_datetime(min_date_str).date()
    max_date = pd.to_datetime(max_date_str).date()

    st.sidebar.markdown("### Период за анализ")
    date_range = st.sidebar.date_input(
        "Избери период",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    # date_input може да върне единична дата или tuple
    if isinstance(date_range, tuple):
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range

    if start_date > end_date:
        st.warning("Началната дата не може да е след крайната. Коригирай периода в sidebar-а.")
        return

    date_from_str = start_date.strftime("%Y-%m-%d")
    date_to_str = end_date.strftime("%Y-%m-%d")

    st.markdown(
        f"### Период: `{date_from_str}` → `{date_to_str}` "
        f"за {format_vendor(vendor_id)}"
    )

    # ===== 1. По дни за избрания vendor (за избрания период) =====
    st.subheader("📅 Оборот по дни (за избрания vendor и период)")

    daily_df, total_revenue, total_qty, avg_per_day = get_vendor_stats_for_period(
        vendor_id, date_from_str, date_to_str
    )

    if daily_df.empty:
        st.info("Няма продажби за този vendor в избрания период.")
    else:
        # дата към datetime
        daily_df["date"] = pd.to_datetime(daily_df["date"])

        # KPIs
        col1, col2, col3 = st.columns(3)
        col1.metric("Общ оборот", f"{total_revenue:,.2f} лв.")
        col2.metric("Общо бройки", f"{total_qty}")
        col3.metric("Среден оборот на ден", f"{avg_per_day:,.2f} лв.")

        # Графика
        st.line_chart(
            daily_df.set_index("date")["total_revenue"],
            height=300,
        )

        # Таблица
        st.dataframe(
            daily_df.sort_values("date", ascending=False),
            use_container_width=True,
        )

    # ===== 2. Детайл по продукти за конкретен ден (drill-down) =====
    st.subheader("🔍 Детайл по продукти за конкретен ден")

    # Вземаме всички налични дати за избрания vendor (извън периода / или само в периода)
    full_daily_df = get_daily_revenue_df(vendor_id)
    if full_daily_df.empty:
        st.info("Няма никакви продажби за този vendor.")
    else:
        full_daily_df["date"] = pd.to_datetime(full_daily_df["date"])
        available_dates = full_daily_df["date"].dt.date.sort_values().unique()

        # Ограничаваме избора само в рамките на периода (по-логично е)
        available_dates_in_period = [d for d in available_dates if start_date <= d <= end_date]
        if not available_dates_in_period:
            available_dates_in_period = available_dates  # fallback: всички дати

        selected_date = st.selectbox(
            "Избери конкретна дата (за детайли по продукти)",
            options=available_dates_in_period,
            format_func=lambda d: d.strftime("%Y-%m-%d"),
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
                use_container_width=True,
            )

    # ===== 3. TOP продукти за периода (за избрания vendor) =====
    st.subheader("🏆 TOP продукти за избрания vendor и период")

    top_df = get_top_products_for_period(vendor_id, date_from_str, date_to_str, limit=20)
    if top_df.empty:
        st.info("Няма продукти с продажби в този период.")
    else:
        st.dataframe(
            top_df,
            use_container_width=True,
        )

    # ===== 4. Overview за всички вендори (за същия период) =====
    st.subheader("🌍 Оборот по вендори за избрания период")

    all_vendors_df = get_all_vendors_revenue_for_period(date_from_str, date_to_str)
    if all_vendors_df.empty:
        st.info("Няма продажби за никой vendor в този период.")
    else:
        # Добавяме колона с име
        all_vendors_df["vendor_name"] = all_vendors_df["vendor_id"].apply(
            lambda vid: VENDOR_NAMES.get(vid, f"Vendor {vid}")
        )

        # Бар графика
        chart_df = all_vendors_df.set_index("vendor_name")["total_revenue"]
        st.bar_chart(chart_df)

        # Таблица
        st.dataframe(
            all_vendors_df[["vendor_id", "vendor_name", "total_revenue"]],
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
