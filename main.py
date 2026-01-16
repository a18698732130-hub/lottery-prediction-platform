import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time
import os
import hashlib

from core.data import DataLoader
from core.lottery import GameType, get_config
from core.analysis import Simulator, Predictor, Backtester, calculate_omission
from core.storage import Storage
from core.prize import PrizeCalculator
from core.auth import AuthManager

st.set_page_config(page_title="彩票分析预测平台", layout="wide", initial_sidebar_state="expanded")

# --- Auth & Session ---
if 'user' not in st.session_state:
    AuthManager().login_form()
    st.stop()

user_id = st.session_state['user']

# --- Initialization ---
@st.cache_resource
def get_data_loader():
    return DataLoader()

dl = get_data_loader()
storage = Storage()

# --- Sidebar ---
st.sidebar.title(f"👤 {user_id}")
if st.sidebar.button("退出登录"):
    del st.session_state['user']
    st.rerun()

st.sidebar.divider()
st.sidebar.title("功能菜单")

game_choice = st.sidebar.selectbox("选择彩种", ["双色球 (SSQ)", "大乐透 (DLT)"])
game_type = GameType.SSQ if "SSQ" in game_choice else GameType.DLT
config = get_config(game_type)

mode = st.sidebar.radio("选择模式", [
    "数据走势 (Dashboard)", 
    "智能预测 (Prediction)", 
    "策略回测 (Backtest)", 
    "模拟投注 (My Bets)",
    "模拟摇奖 (Simulator)" 
])

# --- Data Loading & Auto-Update ---
data_load_state = st.sidebar.text('正在检查数据...')
# Auto-update logic is inside load_data (checks file mtime)
df = dl.load_data(game_type)
data_load_state.text(f"数据已就绪: {len(df)} 期")

if 'date' not in df.columns:
    st.sidebar.warning("⚠️ 数据缺少日期列，建议更新")

if st.sidebar.button("强制更新数据"):
    df = dl.load_data(game_type, force_update=True)
    st.sidebar.success("数据已更新!")
    time.sleep(1)
    st.rerun()

# --- Auto Verification of Pending Bets ---
def verify_pending_bets():
    # Only verify if we have data
    if df.empty: return
    
    my_bets = storage.load_bets(user_id)
    if my_bets.empty: return
    
    # Filter for pending bets of current game type
    pending = my_bets[(my_bets['status'] == 'pending') & (my_bets['game_type'] == game_type.value)]
    
    updates = 0
    for idx, row in pending.iterrows():
        # Match issue
        match = df[df['issue'] == str(row['issue'])]
        if not match.empty:
            actual_row = match.iloc[0]
            if game_type == GameType.SSQ:
                act_reds = [int(actual_row[f'red{j}']) for j in range(1, 7)]
                act_blues = [int(actual_row['blue'])]
            else:
                act_reds = [int(actual_row[f'red{j}']) for j in range(1, 6)]
                act_blues = [int(actual_row[f'blue{j}']) for j in range(1, 3)]
            
            try:
                bet_reds = eval(row['reds']) if isinstance(row['reds'], str) else row['reds']
                bet_blues = eval(row['blues']) if isinstance(row['blues'], str) else row['blues']
                
                red_hits = len(set(bet_reds) & set(act_reds))
                blue_hits = len(set(bet_blues) & set(act_blues))
                
                prize_res = PrizeCalculator.calculate(game_type, red_hits, blue_hits)
                storage.update_bet_status(row['id'], prize_res.level, prize_res.amount)
                updates += 1
            except Exception as e:
                print(f"Error verifying bet {row['id']}: {e}")

    if updates > 0:
        st.toast(f"自动核验完成：更新了 {updates} 条中奖记录！", icon="💰")

# Run verification on load
if 'verified' not in st.session_state:
    verify_pending_bets()
    st.session_state.verified = True

# --- Helpers ---
def get_next_draw_time(game_type):
    now = datetime.now()
    if game_type == GameType.SSQ:
        # Tue(1), Thu(3), Sun(6) 21:15
        draw_days = [1, 3, 6]
        draw_time = "21:15"
    else:
        # Mon(0), Wed(2), Sat(5) 21:25
        draw_days = [0, 2, 5]
        draw_time = "21:25"
    
    # Simple logic to find next
    for i in range(0, 7):
        future = now + timedelta(days=i)
        if future.weekday() in draw_days:
            # If today, check time
            target = datetime.strptime(f"{future.strftime('%Y-%m-%d')} {draw_time}", "%Y-%m-%d %H:%M")
            if target > now:
                return target
    return now # Should not happen

def draw_balls(reds, blues):
    html = '<div style="display: flex; gap: 5px; flex-wrap: wrap;">'
    for r in reds:
        html += f'<div style="width: 32px; height: 32px; background-color: #f44336; border-radius: 50%; color: white; display: flex; align-items: center; justify_content: center; font-weight: bold; font-size: 14px;">{r}</div>'
    for b in blues:
        html += f'<div style="width: 32px; height: 32px; background-color: #2196f3; border-radius: 50%; color: white; display: flex; align-items: center; justify_content: center; font-weight: bold; font-size: 14px;">{b}</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def get_daily_seed(user_id):
    date_str = datetime.now().strftime("%Y%m%d")
    seed_str = f"{date_str}_{user_id}"
    return int(hashlib.sha256(seed_str.encode()).hexdigest(), 16) % (2**32)

# --- Info Section ---
next_draw = get_next_draw_time(game_type)
time_delta = next_draw - datetime.now()
hours = int(time_delta.total_seconds() // 3600)
mins = int((time_delta.total_seconds() % 3600) // 60)

st.info(f"📅 **下期开奖**: {next_draw.strftime('%Y-%m-%d %H:%M')} ({hours}小时{mins}分后) | 🏆 **奖池**: 滚存高额奖金")

with st.expander("查看玩法规则与奖金表"):
    if game_type == GameType.SSQ:
        st.markdown("""
        **双色球规则**: 红球33选6，蓝球16选1。
        - **一等奖 (6+1)**: 浮动奖，最高1000万
        - **二等奖 (6+0)**: 浮动奖
        - **三等奖 (5+1)**: 3000元
        - **四等奖 (5+0/4+1)**: 200元
        - **五等奖 (4+0/3+1)**: 10元
        - **六等奖 (2+1/1+1/0+1)**: 5元
        """)
    else:
        st.markdown("""
        **大乐透规则**: 红球35选5，蓝球12选2。
        - **一等奖 (5+2)**: 浮动奖，最高1000万
        - **二等奖 (5+1)**: 浮动奖
        - **三等奖 (5+0)**: 10000元
        - **...**: (详见官网)
        - **九等奖 (3+0/2+1/...)**: 5元
        """)

# --- Main Views ---

if mode == "数据走势 (Dashboard)":
    st.title("📊 数据走势分析")
    
    file_path = dl.get_data_path(game_type)
    if os.path.exists(file_path):
        mtime = os.path.getmtime(file_path)
        last_update = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
        st.caption(f"📅 数据最后更新: {last_update}")

    tab1, tab2, tab3 = st.tabs(["历史数据", "冷热分析", "遗漏分析"])
    
    with tab1:
        st.subheader("历史数据概览")
        display_df = df.copy()
        
        # Optimize for mobile: Select only essential columns
        cols = []
        display_cols = []
        if game_type == GameType.SSQ:
            cols = ['issue', 'date', 'red1', 'red2', 'red3', 'red4', 'red5', 'red6', 'blue']
            display_cols = ['期号', '日期', '红1', '红2', '红3', '红4', '红5', '红6', '蓝']
        else:
            cols = ['issue', 'date', 'red1', 'red2', 'red3', 'red4', 'red5', 'blue1', 'blue2']
            display_cols = ['期号', '日期', '红1', '红2', '红3', '红4', '红5', '蓝1', '蓝2']
        
        # Handle missing date column gracefully
        if 'date' not in display_df.columns:
            cols.remove('date')
            display_cols.remove('日期')
            
        try:
            display_df = display_df[cols]
            display_df.columns = display_cols
            st.dataframe(
                display_df.sort_values('期号', ascending=False).head(20), 
                use_container_width=True,
                hide_index=True
            )
        except Exception as e:
             st.error(f"数据列格式错误: {e}")

    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔥 红球热度")
            red_cols = [c for c in df.columns if 'red' in c]
            all_reds = df[red_cols].values.flatten()
            red_counts = pd.Series(all_reds).value_counts().sort_index()
            fig_red = px.bar(x=red_counts.index, y=red_counts.values)
            fig_red.update_traces(marker_color='#f44336')
            st.plotly_chart(fig_red, use_container_width=True)
            
        with col2:
            st.subheader("💧 蓝球热度")
            blue_cols = [c for c in df.columns if 'blue' in c]
            all_blues = df[blue_cols].values.flatten()
            blue_counts = pd.Series(all_blues).value_counts().sort_index()
            fig_blue = px.bar(x=blue_counts.index, y=blue_counts.values)
            fig_blue.update_traces(marker_color='#2196f3')
            st.plotly_chart(fig_blue, use_container_width=True)

    with tab3:
        st.subheader("📉 红球遗漏")
        omission = calculate_omission(df, config.red_range[1], 'red')
        omission_series = pd.Series(omission).sort_index()
        fig_omission = px.bar(x=omission_series.index, y=omission_series.values)
        fig_omission.update_traces(marker_color='#FF9800')
        st.plotly_chart(fig_omission, use_container_width=True)

elif mode == "智能预测 (Prediction)":
    st.title("🔮 智能预测")
    
    st.info("💡 算法已集成：012路比、奇偶比、质合比、跨度分析及自动参数调优。")
    
    count = st.number_input("推荐注数", min_value=1, max_value=20, value=5, step=1)
    
    if st.button("生成智能推荐", type="primary"):
        date_str = datetime.now().strftime("%Y-%m-%d")
        existing_pred = storage.db.get_daily_recommendation(user_id, date_str, game_type.value)
        
        predictions = []
        if existing_pred:
            if len(existing_pred) >= count:
                 predictions = existing_pred[:count]
                 st.success(f"已加载今日推荐 (共{len(existing_pred)}注)")
            else:
                 needed = count - len(existing_pred)
                 daily_seed = get_daily_seed(user_id)
                 new_preds = Predictor.predict_many(game_type, df, needed, seed_base=daily_seed + len(existing_pred))
                 predictions = existing_pred + new_preds
                 storage.db.save_daily_recommendation(user_id, date_str, game_type.value, predictions)
                 st.success("已补充生成新号码")
        else:
            daily_seed = get_daily_seed(user_id)
            predictions = Predictor.predict_many(game_type, df, count, seed_base=daily_seed)
            storage.db.save_daily_recommendation(user_id, date_str, game_type.value, predictions)
            
        st.session_state.prediction_result = predictions
        
    if 'prediction_result' in st.session_state and st.session_state.prediction_result:
        predictions = st.session_state.prediction_result
        st.subheader("今日推荐")
        
        last_issue = df.iloc[-1]['issue']
        try:
            next_issue = str(int(last_issue) + 1)
        except:
            next_issue = "Unknown"
            
        for i, (reds, blues) in enumerate(predictions, start=1):
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.caption(f"第 {i} 注")
                    draw_balls(reds, blues)
                with col2:
                    if st.button("保存", key=f"save_{i}"):
                        storage.save_bet(game_type, next_issue, reds, blues, f"智能推荐-{i}", user_id=user_id)
                        st.toast(f"第 {i} 注已保存", icon="✅")
        
        if st.button("一键保存所有", type="secondary"):
             for i, (reds, blues) in enumerate(predictions, start=1):
                 storage.save_bet(game_type, next_issue, reds, blues, f"智能推荐-批量", user_id=user_id)
             st.success(f"已保存 {len(predictions)} 注！")

elif mode == "策略回测 (Backtest)":
    st.title("📈 策略回测")
    
    algo = st.selectbox("选择算法", [
        "增强型智能趋势算法 (Enhanced Smart Trend)",
        "随机选号 (Random)", 
        "热号加权 (Frequency Weighted)",
        "遗漏回补 (Omission Rebound)"
    ], format_func=lambda x: x.split(" (")[0] if "(" in x else x)
    
    col1, col2 = st.columns(2)
    with col1:
        test_count = st.slider("回测期数", 10, 100, 30)
    with col2:
        bets_per_issue = st.number_input("每期注数", 1, 100, 5)
    
    if st.button("开始回测"):
        progress_bar = st.progress(0)
        with st.spinner("计算中..."):
            strategy = None
            if algo == "随机选号 (Random)":
                strategy = Predictor.random_predict
            elif algo == "热号加权 (Frequency Weighted)":
                strategy = Predictor.frequency_predict
            elif algo == "遗漏回补 (Omission Rebound)":
                strategy = Predictor.omission_predict
            elif algo == "增强型智能趋势算法 (Enhanced Smart Trend)":
                strategy = Predictor.composite_predict
                
            res_df = Backtester.run_backtest(game_type, strategy, df, test_count, bets_per_issue=bets_per_issue, progress_callback=progress_bar.progress)
            progress_bar.progress(100)
            
            if not res_df.empty:
                st.success("完成！")
                total_cost = res_df['cost'].sum()
                total_win = res_df['prize'].sum()
                roi = (total_win - total_cost) / total_cost * 100 if total_cost > 0 else 0
                win_rate = (len(res_df[res_df['prize'] > 0]) / len(res_df) * 100)
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("投入", f"¥{total_cost}")
                c2.metric("收益", f"¥{total_win}")
                c3.metric("ROI", f"{roi:.1f}%", delta_color="normal" if roi < 0 else "inverse")
                c4.metric("中奖率", f"{win_rate:.1f}%")
                
                st.line_chart(res_df.set_index('issue')['net_profit'].cumsum())
                
                st.dataframe(
                    res_df[['issue', 'prize', 'hits_summary']].rename(columns={'issue':'期号', 'prize':'奖金', 'hits_summary':'命中'}),
                    use_container_width=True
                )

elif mode == "模拟投注 (My Bets)":
    st.title("📝 模拟投注")
    
    tab1, tab2 = st.tabs(["手动投注", "投注记录"])
    
    with tab1:
        with st.form("bet_form"):
            red_input = st.text_input(f"红球 (逗号分隔)", placeholder="01,05,12,18,25,30")
            blue_input = st.text_input(f"蓝球", placeholder="08")
            note = st.text_input("备注")
            if st.form_submit_button("提交"):
                try:
                    reds = sorted([int(x) for x in red_input.replace("，", ",").split(",") if x.strip()])
                    blues = sorted([int(x) for x in blue_input.replace("，", ",").split(",") if x.strip()])
                    if len(reds) != config.red_count or len(blues) != config.blue_count:
                        st.error("号码数量错误")
                    else:
                        last_issue = df.iloc[-1]['issue']
                        next_issue = str(int(last_issue) + 1)
                        storage.save_bet(game_type, next_issue, reds, blues, note, user_id=user_id)
                        st.success("已保存")
                except:
                    st.error("格式错误")

    with tab2:
        my_bets = storage.load_bets(user_id)
        if not my_bets.empty:
            my_bets = my_bets[my_bets['game_type'] == game_type.value]
            # Verify button
            if st.button("手动核验"):
                verify_pending_bets()
                st.rerun()
            
            # Display
            display_bets = my_bets[['created_at', 'issue', 'reds', 'blues', 'prize_level', 'win_amount']].copy()
            display_bets.columns = ['时间', '期号', '红球', '蓝球', '状态', '奖金']
            display_bets['状态'] = display_bets['状态'].fillna('未开奖').replace('', '未开奖')
            st.dataframe(display_bets.sort_values('时间', ascending=False), use_container_width=True)
        else:
            st.info("暂无记录")

elif mode == "模拟摇奖 (Simulator)":
    st.title("🎰 模拟摇奖")
    if st.button("摇一注", type="primary"):
        r, b = Simulator.simulate_draw(game_type)
        draw_balls(r, b)

st.markdown("---")
st.caption("本系统仅供娱乐与技术研究，请理性购彩。")
