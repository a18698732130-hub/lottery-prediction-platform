import streamlit as st
import pandas as pd
import plotly.express as px
from core.data import DataLoader
from core.lottery import GameType, get_config
from core.analysis import Simulator, Predictor, Backtester, calculate_omission
from core.storage import Storage
from core.prize import PrizeCalculator
import os
import time

st.set_page_config(page_title="彩票分析预测平台", layout="wide")

# Initialize Data Loader
@st.cache_resource
def get_data_loader():
    return DataLoader()

dl = get_data_loader()
storage = Storage()

# Sidebar
st.sidebar.title("功能菜单")

# User Isolation (Simple)
user_id = st.sidebar.text_input("当前用户", value="default_user", help="输入用户名以区分不同用户的投注记录")

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

# Load Data
data_load_state = st.sidebar.text('正在加载数据...')
df = dl.load_data(game_type)
data_load_state.text(f"已加载数据: {len(df)} 期")

# Check if Date column exists, if not, recommend update
if 'date' not in df.columns:
    st.sidebar.warning("⚠️ 数据缺少日期列，建议更新")

if st.sidebar.button("强制更新数据"):
    df = dl.load_data(game_type, force_update=True)
    st.sidebar.success("数据已更新!")
    time.sleep(1)
    st.rerun()

# --- Helper Functions ---
def draw_balls(reds, blues):
    """Render balls using HTML/CSS for better visual"""
    html = '<div style="display: flex; gap: 10px;">'
    for r in reds:
        html += f'<div style="width: 40px; height: 40px; background-color: #f44336; border-radius: 50%; color: white; display: flex; align-items: center; justify_content: center; font-weight: bold;">{r}</div>'
    for b in blues:
        html += f'<div style="width: 40px; height: 40px; background-color: #2196f3; border-radius: 50%; color: white; display: flex; align-items: center; justify_content: center; font-weight: bold;">{b}</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# --- Views ---

from datetime import datetime
import hashlib

# --- Prediction Stability Helper ---
def get_daily_seed(user_id):
    """Generate a stable seed based on Date + UserID"""
    date_str = datetime.now().strftime("%Y%m%d")
    seed_str = f"{date_str}_{user_id}"
    # Convert string hash to integer
    return int(hashlib.sha256(seed_str.encode()).hexdigest(), 16) % (2**32)

if mode == "数据走势 (Dashboard)":
    st.title(f"{config.cn_name} - 数据走势分析")
    
    # Data Update Time
    file_path = dl.get_data_path(game_type)
    if os.path.exists(file_path):
        mtime = os.path.getmtime(file_path)
        last_update = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
        st.caption(f"📅 数据最后更新: {last_update}")

    tab1, tab2, tab3 = st.tabs(["历史数据", "冷热分析", "遗漏分析"])
    
    with tab1:
        st.subheader("历史数据概览")
        # Rename columns for display
        display_df = df.copy()
        
        cols = []
        if game_type == GameType.SSQ:
            # Check if date exists
            has_date = 'date' in display_df.columns
            if has_date:
                cols = ['issue', 'date', 'red1', 'red2', 'red3', 'red4', 'red5', 'red6', 'blue']
                display_cols = ['期号', '开奖日期', '红1', '红2', '红3', '红4', '红5', '红6', '蓝球']
            else:
                cols = ['issue', 'red1', 'red2', 'red3', 'red4', 'red5', 'red6', 'blue']
                display_cols = ['期号', '红1', '红2', '红3', '红4', '红5', '红6', '蓝球']
        else:
            has_date = 'date' in display_df.columns
            if has_date:
                cols = ['issue', 'date', 'red1', 'red2', 'red3', 'red4', 'red5', 'blue1', 'blue2']
                display_cols = ['期号', '开奖日期', '红1', '红2', '红3', '红4', '红5', '蓝1', '蓝2']
            else:
                cols = ['issue', 'red1', 'red2', 'red3', 'red4', 'red5', 'blue1', 'blue2']
                display_cols = ['期号', '红1', '红2', '红3', '红4', '红5', '蓝1', '蓝2']
        
        # Reorder and rename
        try:
            display_df = display_df[cols]
            display_df.columns = display_cols
            st.dataframe(display_df.sort_values('期号', ascending=False).head(20), use_container_width=True)
        except KeyError:
             st.error("数据列格式不匹配，请尝试强制更新数据。")

    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("红球频率热度")
            red_cols = [c for c in df.columns if 'red' in c]
            all_reds = df[red_cols].values.flatten()
            red_counts = pd.Series(all_reds).value_counts().sort_index()
            fig_red = px.bar(x=red_counts.index, y=red_counts.values, labels={'x': '号码', 'y': '出现次数'})
            fig_red.update_traces(marker_color='#f44336')
            st.plotly_chart(fig_red, use_container_width=True)
            
        with col2:
            st.subheader("蓝球频率热度")
            blue_cols = [c for c in df.columns if 'blue' in c]
            all_blues = df[blue_cols].values.flatten()
            blue_counts = pd.Series(all_blues).value_counts().sort_index()
            fig_blue = px.bar(x=blue_counts.index, y=blue_counts.values, labels={'x': '号码', 'y': '出现次数'})
            fig_blue.update_traces(marker_color='#2196f3')
            st.plotly_chart(fig_blue, use_container_width=True)

    with tab3:
        st.subheader("红球当前遗漏值")
        omission = calculate_omission(df, config.red_range[1], 'red')
        omission_series = pd.Series(omission).sort_index()
        fig_omission = px.bar(x=omission_series.index, y=omission_series.values, labels={'x': '号码', 'y': '遗漏期数'})
        fig_omission.update_traces(marker_color='#FF9800')
        st.plotly_chart(fig_omission, use_container_width=True)

elif mode == "智能预测 (Prediction)":
    st.title(f"{config.cn_name} - 智能预测")
    
    st.markdown("""
    本模块采用**增强型智能趋势算法**进行推荐，融合了以下策略：
    1. **热度权重**: 优先考虑近期高频出现的“热号”。
    2. **趋势追踪**: 增加对上期“重号”的权重。
    3. **形态过滤**: 确保号码组合中包含至少一组“连号”（如12,13）。
    4. **遗漏保护**: 适当防守极度冷门的号码（防冷号回补）。
    5. **黄金和值**: 过滤掉概率极低的和值组合。
    
    *注：同一用户当天的推荐号码固定，避免频繁刷新导致决策混乱。*
    """)
    
    count = st.number_input("推荐注数", min_value=1, max_value=20, value=5, step=1)
    
    if 'prediction_result' not in st.session_state:
        st.session_state.prediction_result = None

    if st.button("生成智能推荐", type="primary"):
        # Check DB first
        date_str = datetime.now().strftime("%Y-%m-%d")
        existing_pred = storage.db.get_daily_recommendation(user_id, date_str, game_type.value)
        
        predictions = []
        if existing_pred:
            # Check if we need more
            if len(existing_pred) >= count:
                 predictions = existing_pred[:count]
                 st.success(f"已加载今日生成的推荐结果 (共{len(existing_pred)}注，显示前{count}注)")
            else:
                 # Need to generate more
                 needed = count - len(existing_pred)
                 st.info(f"已有 {len(existing_pred)} 注，正在补充生成 {needed} 注...")
                 
                 daily_seed = get_daily_seed(user_id)
                 # Offset seed by existing length to ensure different numbers
                 new_preds = Predictor.predict_many(game_type, df, needed, seed_base=daily_seed + len(existing_pred))
                 
                 predictions = existing_pred + new_preds
                 # Update DB
                 storage.db.save_daily_recommendation(user_id, date_str, game_type.value, predictions)
                 st.success("推荐结果已更新并保存")
        else:
            # Generate new
            # Use stable seed
            daily_seed = get_daily_seed(user_id)
            predictions = Predictor.predict_many(game_type, df, count, seed_base=daily_seed)
            # Save to DB
            storage.db.save_daily_recommendation(user_id, date_str, game_type.value, predictions)
            
        st.session_state.prediction_result = predictions
        
    if st.session_state.prediction_result:
        predictions = st.session_state.prediction_result
        st.subheader("今日推荐结果")
        
        # Try to guess next issue
        last_issue = df.iloc[-1]['issue']
        try:
            next_issue = str(int(last_issue) + 1)
        except:
            next_issue = "Unknown"
            
        for i, (reds, blues) in enumerate(predictions):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**第 {i+1} 注**")
                draw_balls(reds, blues)
            with col2:
                # Button to add to My Bets
                if st.button("保存此注", key=f"save_{i}"):
                    storage.save_bet(game_type, next_issue, reds, blues, f"智能推荐-第{i+1}注", user_id=user_id)
                    st.success(f"第 {i+1} 注已保存！")
        
        if st.button("保存所有推荐号码"):
             for i, (reds, blues) in enumerate(predictions):
                 storage.save_bet(game_type, next_issue, reds, blues, f"智能推荐-批量保存", user_id=user_id)
             st.success(f"成功保存 {len(predictions)} 注号码！")
        
        st.info("注：预测结果仅供娱乐参考，彩票中奖为随机事件。")

elif mode == "策略回测 (Backtest)":
    st.title(f"{config.cn_name} - 策略回测")
    
    algo = st.selectbox("选择回测算法", [
        "增强型智能趋势算法 (Enhanced Smart Trend)",
        "随机选号 (Random)", 
        "热号加权 (Frequency Weighted)",
        "遗漏回补 (Omission Rebound)"
    ], format_func=lambda x: x.split(" (")[0] if "(" in x else x)
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        test_count = st.slider("回测期数", 10, 100, 50, help="为了性能，建议不超过100期")
    with col_t2:
        bets_per_issue = st.number_input("每期投注注数", min_value=1, max_value=100, value=5)
    
    if st.button("开始回测"):
        progress_bar = st.progress(0)
        with st.spinner("正在回测中..."):
            strategy = None
            if algo == "随机选号 (Random)":
                strategy = Predictor.random_predict
            elif algo == "热号加权 (Frequency Weighted)":
                strategy = Predictor.frequency_predict
            elif algo == "遗漏回补 (Omission Rebound)":
                strategy = Predictor.omission_predict
            elif algo == "增强型智能趋势算法 (Enhanced Smart Trend)":
                strategy = Predictor.composite_predict
            # Golden Sum removed from dropdown as it's merged into Composite, but code might still exist in class
                
            res_df = Backtester.run_backtest(game_type, strategy, df, test_count, bets_per_issue=bets_per_issue, progress_callback=progress_bar.progress)
            progress_bar.progress(100) # Ensure full
            
            if not res_df.empty:
                st.success("回测完成！")
                
                # Financials
                total_cost = res_df['cost'].sum()
                total_win = res_df['prize'].sum()
                roi = (total_win - total_cost) / total_cost * 100 if total_cost > 0 else 0
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("总投入", f"¥{total_cost}")
                col2.metric("总奖金", f"¥{total_win}")
                col3.metric("投资回报率 (ROI)", f"{roi:.2f}%", delta_color="normal" if roi < 0 else "inverse")
                win_rate = (len(res_df[res_df['prize'] > 0]) / len(res_df) * 100)
                col4.metric("中奖率 (至少一注中奖)", f"{win_rate:.1f}%")
                
                st.subheader("资金曲线")
                res_df['累计盈亏'] = (res_df['prize'] - res_df['cost']).cumsum()
                fig = px.line(res_df, x='issue', y='累计盈亏', title="累计盈亏走势 (元)")
                fig.update_layout(xaxis_title="期号", yaxis_title="累计盈亏")
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("详细回测记录")
                # Rename columns for display
                display_res = res_df[['issue', 'bets_count', 'cost', 'prize', 'hits_summary']].copy()
                display_res.columns = ['期号', '投注注数', '投入金额', '中奖金额', '命中详情 (前5注)']
                st.dataframe(display_res, use_container_width=True)
            else:
                st.warning("数据不足以进行回测。")

elif mode == "模拟投注 (My Bets)":
    st.title(f"{config.cn_name} - 模拟投注记录")
    
    tab1, tab2 = st.tabs(["手动投注", "投注记录"])
    
    with tab1:
        st.subheader("手动输入号码")
        st.caption(f"格式说明: 红球用逗号分隔，蓝球用逗号分隔。例如 SSQ: 1,2,3,4,5,6 + 1")
        
        with st.form("manual_bet_form"):
            red_input = st.text_input(f"红球号码 ({config.red_count}个, 范围 {config.red_range[0]}-{config.red_range[1]})", placeholder="例如: 01,05,12,18,25,30")
            blue_input = st.text_input(f"蓝球号码 ({config.blue_count}个, 范围 {config.blue_range[0]}-{config.blue_range[1]})", placeholder="例如: 08")
            note = st.text_input("备注 (可选)")
            
            submitted = st.form_submit_button("确认投注")
            
            if submitted:
                # Validation
                try:
                    # Replace Chinese comma with English comma
                    red_str = red_input.replace("，", ",")
                    blue_str = blue_input.replace("，", ",")
                    
                    reds = [int(x.strip()) for x in red_str.split(",") if x.strip()]
                    blues = [int(x.strip()) for x in blue_str.split(",") if x.strip()]
                    
                    # Sort
                    reds.sort()
                    blues.sort()
                    
                    errors = []
                    if len(reds) != config.red_count:
                        errors.append(f"红球数量错误: 需要 {config.red_count} 个，实际 {len(reds)} 个")
                    if len(blues) != config.blue_count:
                        errors.append(f"蓝球数量错误: 需要 {config.blue_count} 个，实际 {len(blues)} 个")
                    
                    # Range check
                    if any(r < config.red_range[0] or r > config.red_range[1] for r in reds):
                        errors.append(f"红球超出范围 {config.red_range}")
                    if any(b < config.blue_range[0] or b > config.blue_range[1] for b in blues):
                        errors.append(f"蓝球超出范围 {config.blue_range}")
                        
                    if len(set(reds)) != len(reds):
                        errors.append("红球包含重复号码")
                    if len(set(blues)) != len(blues):
                         # DLT blue balls must be unique? Yes.
                         errors.append("蓝球包含重复号码")

                    if errors:
                        for e in errors:
                            st.error(e)
                    else:
                        # Success
                        last_issue = df.iloc[-1]['issue']
                        try:
                            next_issue = str(int(last_issue) + 1)
                        except:
                            next_issue = "Unknown"
                            
                        storage.save_bet(game_type, next_issue, reds, blues, note)
                        st.success(f"投注已保存！期号: {next_issue} 号码: {reds} + {blues}")
                        
                except ValueError:
                    st.error("输入格式错误，请输入数字并用逗号分隔")

    with tab2:
        st.subheader("我的投注历史")
        my_bets = storage.load_bets()
        if not my_bets.empty:
            # Filter by game type
            my_bets = my_bets[my_bets['game_type'] == game_type.value]
            
            # Fill NaN
            my_bets['prize_level'] = my_bets['prize_level'].fillna("未开奖")
            my_bets['prize_level'] = my_bets['prize_level'].replace("", "未开奖")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("检查中奖情况"):
                    # Logic to check against loaded history
                    updates = 0
                    for idx, row in my_bets.iterrows():
                        if row['status'] == 'checked':
                            continue
                            
                        match = df[df['issue'] == str(row['issue'])]
                        if not match.empty:
                            # Calculate
                            actual_row = match.iloc[0]
                            if game_type == GameType.SSQ:
                                act_reds = [int(actual_row[f'red{j}']) for j in range(1, 7)]
                                act_blues = [int(actual_row['blue'])]
                            else:
                                act_reds = [int(actual_row[f'red{j}']) for j in range(1, 6)]
                                act_blues = [int(actual_row[f'blue{j}']) for j in range(1, 3)]
                                
                            bet_reds = eval(row['reds'])
                            bet_blues = eval(row['blues'])
                            
                            red_hits = len(set(bet_reds) & set(act_reds))
                            blue_hits = len(set(bet_blues) & set(act_blues))
                            
                            prize_res = PrizeCalculator.calculate(game_type, red_hits, blue_hits)
                            
                            storage.update_bet_status(row['id'], prize_res.level, prize_res.amount)
                            updates += 1
                    
                    if updates > 0:
                        st.success(f"更新了 {updates} 条记录的中奖状态！")
                        st.rerun()
                    else:
                        st.info("没有发现新的开奖结果匹配。")
            
            # Display nicely
            st.dataframe(
                my_bets[['created_at', 'issue', 'reds', 'blues', 'prize_level', 'win_amount', 'note']].sort_values('created_at', ascending=False), 
                use_container_width=True,
                column_config={
                    "created_at": "投注时间",
                    "issue": "期号",
                    "reds": "红球",
                    "blues": "蓝球",
                    "prize_level": "中奖情况",
                    "win_amount": "奖金",
                    "note": "备注"
                }
            )
        else:
            st.info("暂无投注记录。")

elif mode == "模拟摇奖 (Simulator)":
    st.title(f"{config.cn_name} - 模拟摇奖")
    
    if st.button("开始摇奖", type="primary"):
        reds, blues = Simulator.simulate_draw(game_type)
        st.write("### 摇奖结果:")
        draw_balls(reds, blues)

st.markdown("---")
st.caption("Disclaimer: 本平台仅用于数据分析与模拟，不提供任何购彩服务，也不保证预测准确性。彩票有风险，购买需谨慎。")
