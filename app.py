import itertools
import pandas as pd
import streamlit as st

st.set_page_config(page_title='尽膳尽美｜片区画像智能选品', page_icon='🥬', layout='wide')

# Report-derived conjoint utilities and segment weights.
UTILITIES = {
    '新鲜度': {'当日现切': .42, '冷藏1-2日': -.05, '冷冻保存': -.37},
    '卫生安全': {'权威检测报告': .38, '品牌溯源': .15, '商家自检': -.53},
    '价格溢价': {'溢价10%': .40, '溢价30%': .08, '溢价50%': -.48},
    '处理方式': {'清洗切分': .22, '仅清洗': -.22},
    '销售渠道': {'线下超市': .18, '电商平台': .05, '社区团购': -.23},
}
OVERALL = {'卫生安全': 28.5, '新鲜度': 24.2, '价格溢价': 22.8, '处理方式': 13.1, '销售渠道': 11.4}
PERSONAS = {
    '品质追求型': {'卫生安全': 34.8, '新鲜度': 28.5, '价格溢价': 15.2, '处理方式': 11.5, '销售渠道': 10.0},
    '价格敏感型': {'卫生安全': 6.2, '新鲜度': 8.4, '价格溢价': 68.5, '处理方式': 8.2, '销售渠道': 8.7},
    '便捷导向型': {'卫生安全': 21.5, '新鲜度': 22.8, '价格溢价': 23.4, '处理方式': 25.2, '销售渠道': 7.1},
}

# These are transparent business-rule mappings, not demographic coefficients estimated by the report.
AREA_TO_PERSONA = {
    '学生较多': {'品质追求型': 0.10, '价格敏感型': 0.70, '便捷导向型': 0.20},
    '白领较多': {'品质追求型': 0.30, '价格敏感型': 0.15, '便捷导向型': 0.55},
    '老年人较多': {'品质追求型': 0.45, '价格敏感型': 0.40, '便捷导向型': 0.15},
    '年轻租住人群较多': {'品质追求型': 0.15, '价格敏感型': 0.30, '便捷导向型': 0.55},
    '小家庭/双职工家庭较多': {'品质追求型': 0.20, '价格敏感型': 0.20, '便捷导向型': 0.60},
    '收入水平整体较高': {'品质追求型': 0.60, '价格敏感型': 0.10, '便捷导向型': 0.30},
    '预算约束明显': {'品质追求型': 0.10, '价格敏感型': 0.75, '便捷导向型': 0.15},
}


def normalized_score(row, persona_weights):
    total = 0.0
    for attr, levels in UTILITIES.items():
        lo, hi = min(levels.values()), max(levels.values())
        value = (levels[row[attr]] - lo) / (hi - lo) * 100 if hi != lo else 50
        total += persona_weights[attr] / 100 * value
    return round(total, 1)


def get_persona_mix(selected_traits):
    mix = {p: 0.0 for p in PERSONAS}
    for trait in selected_traits:
        for persona, weight in AREA_TO_PERSONA[trait].items():
            mix[persona] += weight
    n = max(len(selected_traits), 1)
    return {p: v / n for p, v in mix.items()}


def blended_weights(mix):
    weights = {}
    for attr in OVERALL:
        weights[attr] = sum(mix[p] * PERSONAS[p][attr] for p in PERSONAS)
    total = sum(weights.values())
    return {a: v / total * 100 for a, v in weights.items()}


def score_blended(row, weights):
    result = 0.0
    for attr, levels in UTILITIES.items():
        lo, hi = min(levels.values()), max(levels.values())
        value = (levels[row[attr]] - lo) / (hi - lo) * 100 if hi != lo else 50
        result += weights[attr] / 100 * value
    return round(result, 1)


def recommendations(mix, traits, weights):
    lead = max(mix, key=mix.get)
    price_weight = weights['价格溢价']
    process_weight = weights['处理方式']
    freshness_weight = weights['新鲜度']
    quality_weight = weights['卫生安全']

    # Product combination is selected by scoring all supported combinations against the inferred segment mix.
    all_rows = []
    for vals in itertools.product(*[list(UTILITIES[a]) for a in UTILITIES]):
        row = dict(zip(UTILITIES, vals))
        row['画像匹配分'] = score_blended(row, weights)
        all_rows.append(row)
    ranked = pd.DataFrame(all_rows).sort_values('画像匹配分', ascending=False).reset_index(drop=True)
    best = ranked.iloc[0].to_dict()

    if price_weight >= 30 or '学生较多' in traits or '预算约束明显' in traits:
        pricing = '建议以 10% 溢价作为主力测试档；用基础款/促销款控制门槛，暂不把 30% 或 50% 溢价作为主推。'
    elif quality_weight >= 28 and '收入水平整体较高' in traits:
        pricing = '建议以 10% 溢价为主，少量测试 30% 溢价的高品质款；高溢价需用检测、溯源和新鲜度证明价值。'
    else:
        pricing = '建议以 10% 溢价为主力档，保留少量 30% 溢价差异化款；根据真实成交反馈再调整。'

    if process_weight >= 20 or '白领较多' in traits or '年轻租住人群较多' in traits or '小家庭/双职工家庭较多' in traits:
        assortment = '以清洗切分、可快速下锅的净菜为主；搭配单人份/双人份、小包装和快手菜组合。'
    elif '老年人较多' in traits:
        assortment = '以易辨认、易烹饪、份量适中的基础蔬菜组合为主；标注清晰的日期、储存方式和烹饪建议。'
    else:
        assortment = '以高频基础菜、家庭常用组合为主，少量配置清洗切分的便捷款。'

    if '老年人较多' in traits:
        delivery = '优先考虑线下销售点/社区便利自提，配合清晰标价与人工咨询；若开配送，先做固定时段、短距离配送。'
    elif '学生较多' in traits:
        delivery = '建议采用线上预订 + 校园周边固定自提点/集中配送，集中订单以控制履约成本。'
    elif '白领较多' in traits or '年轻租住人群较多' in traits or '小家庭/双职工家庭较多' in traits:
        delivery = '建议线上下单 + 下班前后时段配送/社区自提并行；优先测试预约配送，避免承诺未经验证的即时达。'
    else:
        delivery = '建议线下展示销售与线上预订/社区自提并行，按订单密度决定是否增加配送。'

    if quality_weight >= 27:
        trust = '将权威检测信息、批次/产地溯源和加工日期放在醒目位置。'
    else:
        trust = '基础安全信息必须清晰展示；在价格沟通之外，持续突出加工日期、储存方式和来源信息。'
    if freshness_weight >= 23:
        freshness = '优先小批量、较高频补货，明确加工/包装日期；避免为追求品类数量而压库存。'
    else:
        freshness = '优先稳定供应高频品类，结合销售记录逐步调整补货频率。'
    return lead, best, ranked, assortment, pricing, delivery, trust, freshness


st.title('🥬 尽膳尽美｜片区画像智能选品')
st.caption('输入销售点周边居民特征，自动生成净菜选品、价格与履约建议')
st.info('研究基础：994 份有效问卷口径；消费者细分与属性效用来自调研报告。片区特征到消费画像的映射、配送建议属于可解释的经营规则，不是报告直接估计的因果系数；请用实际销售反馈持续校准。')

with st.form('area_profile'):
    st.subheader('1. 描述销售点周边居民')
    traits = st.multiselect(
        '选择符合该片区的特征（可多选）',
        list(AREA_TO_PERSONA.keys()),
        default=['白领较多', '小家庭/双职工家庭较多'],
        help='尽量选择最明显的 1—4 项。选择越贴近实际，建议越有参考价值。',
    )
    area_name = st.text_input('片区/销售点名称（选填）', placeholder='例如：某大学北门社区店')
    st.subheader('2. 补充经营条件（选填）')
    c1, c2, c3 = st.columns(3)
    with c1:
        budget = st.selectbox('目标价格定位', ['大众平价', '平价为主、品质兼顾', '品质优先'], index=1)
    with c2:
        fulfillment = st.selectbox('当前履约能力', ['仅线下销售', '可做自提/团购', '具备短距离配送'], index=1)
    with c3:
        store_size = st.selectbox('销售点规模', ['小型社区点', '中型门店', '较大型门店'], index=0)
    submitted = st.form_submit_button('生成片区选品方案', type='primary', use_container_width=True)

if submitted:
    if not traits:
        st.warning('请至少选择一项居民特征，再生成方案。')
    else:
        mix = get_persona_mix(traits)
        weights = blended_weights(mix)
        lead, best, ranked, assortment, pricing, delivery, trust, freshness = recommendations(mix, traits, weights)
        if budget == '大众平价':
            pricing = '按你选择的“大众平价”定位，建议优先控制加价幅度，主推溢价 10% 档，并用小份装/组合装做价格锚点。'
        elif budget == '品质优先':
            pricing = '按你选择的“品质优先”定位，仍建议从溢价 10% 主力款起步，少量测试 30% 款；必须配套可验证的品质证据，不建议直接大规模推 50% 溢价。'
        if fulfillment == '仅线下销售':
            delivery = '当前仅线下销售：先采用门店自提/到店购买，收集预订需求后再决定是否增加配送。'
        elif fulfillment == '可做自提/团购':
            delivery = delivery + ' 现阶段优先落地自提/团购，配送服务先小范围、固定时段试运行。'
        else:
            delivery = delivery + ' 已具备配送能力，可按固定时段和服务半径设置配送，先跟踪准时率、损耗与单均履约成本。'

        st.divider()
        st.subheader(f'片区方案：{area_name.strip() or "未命名销售点"}')
        st.caption('以下是依据所选特征生成的经营建议，不是销量或利润承诺。')
        cols = st.columns(3)
        cols[0].metric('主要消费画像', lead)
        cols[1].metric('推荐组合匹配分', f'{best["画像匹配分"]}/100')
        cols[2].metric('建议主力溢价', '10%')

        st.markdown('### 推荐执行方案')
        st.markdown(f'**选品模式**\n\n{assortment}')
        st.markdown(f'**价格策略**\n\n{pricing}')
        st.markdown(f'**销售/配送方式**\n\n{delivery}')
        st.markdown(f'**品质与信任展示**\n\n{trust}')
        st.markdown(f'**新鲜度与补货**\n\n{freshness}')

        st.markdown('### 建议优先上架的净菜组合')
        product_cols = st.columns(2)
        with product_cols[0]:
            st.write(f'**新鲜度：** {best["新鲜度"]}')
            st.write(f'**卫生安全：** {best["卫生安全"]}')
            st.write(f'**价格溢价：** {best["价格溢价"]}')
        with product_cols[1]:
            st.write(f'**处理方式：** {best["处理方式"]}')
            st.write(f'**销售渠道：** {best["销售渠道"]}')
            st.write(f'**组合匹配分：** {best["画像匹配分"]}/100')

        st.markdown('### 片区画像推断')
        mix_df = pd.DataFrame([{'消费画像': p, '估计权重（规则推断）': round(v * 100, 1)} for p, v in mix.items()]).sort_values('估计权重（规则推断）', ascending=False)
        st.bar_chart(mix_df.set_index('消费画像'))
        st.caption('“估计权重”是将你选择的居民特征映射到报告中的三类画像后得到的规则权重，不代表该片区真实人口比例。')

        with st.expander('查看匹配分靠前的 10 种组合'):
            st.dataframe(ranked.head(10), hide_index=True, use_container_width=True)
        export = ranked.copy()
        export.insert(0, '片区名称', area_name.strip() or '未命名销售点')
        st.download_button('下载全部候选组合 CSV', export.to_csv(index=False).encode('utf-8-sig'), '片区净菜选品方案.csv', 'text/csv')

        st.markdown('### 落地后建议记录的数据')
        st.write('至少记录每日销量、售罄时间、报损量、顾客反馈、实际成交溢价、订单来源与配送成本。积累数据后，才能进一步把规则建议校准为该销售点自己的经营模型。')
else:
    st.markdown('### 使用方式')
    st.write('1. 勾选该片区的主要居民特征。')
    st.write('2. 选择销售点的价格定位和履约能力。')
    st.write('3. 点击“生成片区选品方案”，获得选品组合、价格溢价、渠道/配送方式和品质展示建议。')
    st.markdown('### 当前模型依据')
    st.write('报告将消费者划分为品质追求型、价格敏感型、便捷导向型，并测量了新鲜度、卫生安全、价格溢价、处理方式和销售渠道的相对偏好。平台将这些参数用于候选组合排序。')
    st.caption('注意：报告没有提供逐份问卷原始数据，也没有提供配送方式的专门效用估计，因此平台不会声称重新训练统计模型或将配送建议说成报告的实证结论。')

st.divider()
st.caption('尽膳尽美 · 片区画像智能选品工具 · 研究参数 + 可解释经营规则')
