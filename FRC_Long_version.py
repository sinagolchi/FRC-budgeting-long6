import streamlit as st
import pandas as pd
import psycopg2
import time
import pytz

st.set_page_config(layout='wide') #set streamlit page to wide mode
user_dict = {
    'M':'Mayor',
    'LEF':'Large Engineering Firm',
    'DP': 'District Planner',
    'EM': 'Emergency Manager',
    'ENGO': 'Environmental ENGO',
    'F': 'Farmer',
    'FP': 'Federal Government',
    'FN': 'First Nations',
    'I': 'Insurance Company',
    'J': 'Journalist',
    'LD': 'Land Developer',
    'LBO': 'Local Business',
    'PUC': 'Power Utility',
    'CRA-HV': 'Community Residence - High Value',
    'CRA-MHA': 'Community Residence - Mobile Home',
    'CRA-MV': ' Community Residence - Mediume value',
    'PH': 'Hydrologist',
    'PP': 'Provincial Politician',
    'TA': 'Transport Authority',
    'WW': 'Waste and Water Treatment Director'
}
user_dict_inv= {v:k for k,v in user_dict.items()}

def init_connection():
    return psycopg2.connect(**st.secrets["postgres"])

conn = init_connection()


def get_sql(table):
    return pd.read_sql("SELECT * from " + table+";",conn)

df = get_sql('budget_lb1')

df_m = get_sql('measures_lb1')
with st.expander('Developer tools'):
    st.dataframe(df_m)

# st.write(list(df_m[df_m['type']=='Social']['measure_id']))

st.title('FRC Game companion WebApp')
st.caption('Developed by Sina Golchi with collaboration with FRC Team under creative commons license')

#sidebar and login system
with st.sidebar:
    st.write('Please Login below:')
    board = st.selectbox(label='FRC Board number',options=[1,2,3,4,5])
    user_id = st.text_input('Your unique FRC ID')
    df_v = get_sql('frc_long_variables')
    df_v.set_index('board',inplace=True)
    round = df_v.loc[board,'round']
    #st.metric(label='Game round', value=df_v.loc[board,'round'])

try:
    st.header("Your role is: " + str(user_dict[user_id]) + " on board " + str(board))
except:
    if user_id == '':
        st.warning('You are not logged in! Please login from the sidebar on the left.\n'
                   'If sidebar is hidden reveal it via the arrow on the upper left of this page')
        st.stop()
    else:
        st.error('Your unique ID is incorrect, please contact FRC admins for help!')
        st.stop()


other_roles = [x for x in user_dict.keys() if x != user_id]
# st.write(len(other_roles))

df.set_index('role',inplace=True)
df_m.set_index('measure_id',inplace=True)

st.header('Your budget')
st.metric(value='$'+str(df.loc[user_id,'cb']),delta=int(df.loc[user_id,'delta']),label="My Current budget")

st.subheader('Participants budgets')

with st.expander('budgets'):
    metric_cols_1 = st.columns(7)
    metric_cols_2 = st.columns(7)
    metric_cols_3 = st.columns(7)
    metric_cols = metric_cols_1 + metric_cols_2 + metric_cols_3

    for col, role in zip(metric_cols,other_roles):
        with col:
            st.metric(label=user_dict[role],value='$'+str(df.loc[role,'cb']),delta=int(df.loc[role,'delta']))

update_bid_measure = ("UPDATE measures_lb1 SET person_bid = %s, total_bid = total_bid + %s WHERE measure_ID=%s;")
update_bid_role =  ("UPDATE budget_lb1 SET r%s_measure = %s, r%s_bid = %s WHERE role=%s;")
log_bid = ("INSERT INTO measure_log VALUES (NOW(),%s,%s,%s,%s);")

def make_bid_func(measure, amount):
    df = get_sql('budget_lb1')
    df.set_index('role',inplace=True)
    bid_total = sum([int(i) for i in df[df['r' + str(round) + '_measure'] == measure][
                    'r' + str(round) + '_bid'].to_list()])
    if measure in df['r' + str(round) + '_measure'].to_list() and bid_total + amount > df_m.loc[measure,'cost']:

        st.error('The amount you are bidding will increase the total bid ve the cost of measure, consider changing your bid to ' + str(int(df_m.loc[measure,'cost']-bid_total)) +
                 ' or less, or alternatively bid on a different measure')
        time.sleep(3)
        st.experimental_rerun()

    else:
        cur = conn.cursor()
        cur.execute(update_bid_role,(round,measure,round,amount,user_id))
        cur.execute(update_bid_measure, (user_id, amount, measure))
        if df.loc[user_id,'r1_measure'] == None:
            cur.execute(log_bid,('New',user_dict[user_id],amount,measure))
        else:
            cur.execute(log_bid,('Change', user_dict[user_id], amount, measure))
        conn.commit()
        with st.spinner('Registering your bid'):
            time.sleep(3)
        st.success('You bid on ' + measure + ' successfully')
        time.sleep(2)
        st.experimental_rerun()


st.markdown("""___""")
st.header('Biding on features')
col1_f, col2_f, col3_f = st.columns(3)

with col1_f:
    mit_type = st.radio(label='Type of mitigation', options=['Structural','Natural', 'Social'])
    bid_measure = st.selectbox(label='Measures', options=list(df_m[df_m['type']==mit_type].index.values))
with col2_f:
    if int(df_m.loc[bid_measure, 'cost']) != 0:
        st.metric(label='Cost of ' + bid_measure, value=int(df_m.loc[bid_measure, 'cost']))
        bid_amount = st.number_input(value=1, label='how much you would like to bid?', min_value=1)
    else:
        st.markdown('### The cost is covered by taxes')

with col3_f:
    st.metric(label='Your budget if bid successful', value=int(df.loc[user_id, 'cb'] - bid_amount), delta=-bid_amount)
    make_bid = st.button("Make/Change the bid")

if make_bid:
    make_bid_func(bid_measure, bid_amount)

st.subheader('Measures suggested')
for measure in df_m.index.values:
    if measure in df['r' + str(round) + '_measure'].to_list():
        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric(label=measure, value=str(sum([int(i) for i in df[df['r' + str(round) + '_measure'] == measure][
                'r' + str(round) + '_bid'].to_list()])) + r"/" + str(int(df_m.loc[measure, 'cost'])))
        with col2:
            biders = list(df[df['r' + str(round) + '_measure'] == measure].index)
            amounts = df[df['r' + str(round) + '_measure'] == measure]['r' + str(round) + '_bid'].to_list()
            st.caption('Biders: ' + ',  '.join([user_dict[p] + ': $' + str(b) for p, b in zip(biders, amounts)]))
            st.progress(int(sum([int(i) for i in df[df['r' + str(round) + '_measure'] == measure][
                'r' + str(round) + '_bid'].to_list()]) / df_m.loc[measure, 'cost'] * 100))

update_budget = ("UPDATE budget_lb1 SET cb = %s WHERE role=%s;")
update_delta =  ("UPDATE budget_lb1 SET delta = %s WHERE role=%s;")
log_transaction = ("INSERT INTO payment VALUES (NOW(),%s,%s,%s);")

def money_transfer(amount,r_party):
    curA = conn.cursor()
    curA.execute(update_budget,(int(df.loc[user_id,'cb'])-amount,user_id))
    curA.execute(update_delta,(-amount,user_id))
    curA.execute(update_budget,(int(df.loc[r_party,'cb']+amount),r_party))
    curA.execute(update_delta,(+amount,r_party))
    curA.execute(log_transaction,(user_dict[user_id],amount,r_party))
    conn.commit()

st.markdown("""___""")
st.header("Money Transfer")
col1 , col2, col3, col4 = st.columns(4)
with col1:
    t_amount = st.number_input(value=0, label='Budget to transfer',min_value=0)
with col2:
    party = st.selectbox(options=[x for x in other_roles], label='Stakeholder receiving')
with col4:
    transfer = st.button(label='Complete transaction',help='Only click when you are absolutely sure')
with col3:
    st.metric(label='Budget after transaction',value='$'+str(df.loc[user_id,'cb']-t_amount),delta=-t_amount)

if transfer:
    money_transfer(t_amount,party)
    with st.spinner('Performing transaction'):
        time.sleep(3)
    st.success('The transaction to ' + party + ' was successful')
    time.sleep(3)
    st.experimental_rerun()

st.header('Summary')
with st.expander("Bidding summary"):
    df_m_log = pd.read_sql("SELECT * from measure_log;",conn)
    est = pytz.timezone('EST')
    df_m_log = df_m_log.rename(
        columns={'datetime': 'Timestamp', 'bid_type': 'Type of bid', 'person_biding': 'Role of bidder',
                 'amount': 'Amount of bid', 'measure': 'Measure'})
    if not df_m_log.empty:
        df_m_log['Timestamp'] = df_m_log['Timestamp'].dt.tz_convert('EST').dt.strftime('%B %d, %Y, %r')
        st.dataframe(df_m_log)


with st.expander("Transaction summary"):
    df_p_log = pd.read_sql("SELECT * from payment;", conn)
    est = pytz.timezone('EST')
    df_p_log = df_p_log.rename(
        columns={'datetime': 'Timestamp', 'from_user': 'Sender', 'amount': 'Transaction total',
                 'to_user': 'Receiving party'})
    if not df_p_log.empty:
        df_p_log['Timestamp'] = df_p_log['Timestamp'].dt.tz_convert('EST').dt.strftime('%B %d, %Y, %r')
        st.dataframe(df_p_log)

insurance_update = ("UPDATE budget_lb1 SET r%s_insurance = %s WHERE role=%s;")
#function for buying insurance
def insure_me(user, action):
    cur = conn.cursor()
    cur.execute(insurance_update,(round,action,user))
    if action:
        cur.execute(update_budget, (int(df.loc[user_id, 'cb']) - 1, user_id))
        cur.execute(update_delta, (-1, user_id))
        conn.commit()
        with st.spinner('Preparing your policy'):
            time.sleep(2)
        st.success('You are insured :)')
        time.sleep(2)
        st.experimental_rerun()
    else:
        cur.execute(update_budget, (int(df.loc[user_id, 'cb']) + 1, user_id))
        cur.execute(update_delta, (+1, user_id))
        conn.commit()
        with st.spinner('Cancelling your policy'):
            time.sleep(2)
        st.success('Your policy was canceled successfully')
        time.sleep(2)
        st.experimental_rerun()


# Insurance section sidebar
with st.sidebar:
    if user_id =='I':
        st.header('Insurance deals')
        slogan = st.text_input(label='Set your slogan for selling insurance', value=df_v.loc[board,'insurance_slogan'])
        col1, col2 = st.columns(2)
        with col1:
            insurance_price = st.number_input(label='insurance price',value=df_v.loc[board,'insurance_price'])
        with col2:
            st.metric(label='Current Price', value=df_v.loc[board,'insurance_price'])
    else:
        st.header('Flood insurance')
        if not df.loc[user_id,'r'+str(round)+'_insurance']:
            st.warning('You are not insured for round ' + str(round))
            st.subheader('Would you like to purchase insurance?')
            col1, col2 = st.columns(2)
            with col1:
                insure = st.button(label='Buy insurance')
            with col2:
                st.metric(label='Budget preview', value=int(df.loc[user_id,'cb']-1),delta=-1)
            if insure:
                insure_me(user_id, True)
        else:
            st.success('your property is insured for round ' + str(round))
            cancel_policy = st.button(label='Cancel policy')
            if cancel_policy:
                insure_me(user_id,False)
