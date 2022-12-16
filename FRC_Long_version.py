import streamlit as st
import pandas as pd
import psycopg2
import time
import pytz
import streamlit.components.v1 as components
import seaborn as sns

st.set_page_config(layout='wide',page_title='FRC Game Companion',page_icon='FRC Logo White-100px.png') #set streamlit page to wide mode

game_type = 'Simplified'

def refresh():
    st.experimental_rerun()

if game_type == 'full':
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

else:
    user_dict = {'M': "Mayor", 'P': 'Planner', 'EM': 'Emergency Manager', 'CSO': 'Community Service',
                 'WR': 'Waterfront Resident', 'F': 'Farmer', 'LD': 'Land Developer', 'LEF': 'Large Engineering Firm'}
user_dict_inv= {v:k for k,v in user_dict.items()}

phase_dict = {0: 'Adjusting tax rate (for government only)', 3: 'Phase 3: Updating Budget', 1: 'Phase 1: FRM Measure bidding and implementation', 5: 'Phase 1B: Transactions', 2: 'Phase 2: Flood and damage analysis', 4: 'Phase 4: Vote'}


if game_type == 'full':
    def init_connection():
        return psycopg2.connect(**st.secrets["postgres"])
else:
    def init_connection():
        return psycopg2.connect(options='-c search_path=FRC_s',**st.secrets["postgres"])

conn = init_connection()


def get_sql(table):
    return pd.read_sql("SELECT * from " + table+";",conn)

def choose_role(user:str,board:int):
    with st.container():
        st.info('It seems that you do not have a role yet, please choose one below:')
        st.warning('Note: If the role you chose is taken already you will receive a prompt to choose another')
        dfr = get_sql('frc_users')
        dfr.set_index('user',inplace=True)
        chosen_roles = list(dfr[dfr['board'] == board]['role'])
        print(chosen_roles)
        roles = user_dict.keys()
        role_options = [user_dict[role] for role in roles if role not in chosen_roles]
        role_selection = st.radio(label='Choose a role and confirm', options=role_options)
        def confirm_selection(selection,user_name):
            dfr = get_sql('frc_users')
            dfr.set_index('user',inplace=True)
            dfr = dfr[dfr['board']==board]
            print(dfr)
            if selection not in dfr['role']:
                curB = conn.cursor()
                try:
                    curB.execute("UPDATE frc_users SET role=%s WHERE name=%s;",(user_dict_inv[selection],str(dfr.loc[user_name,'name'])))
                    conn.commit()
                except:
                    st.error('This role was taken just now, try again.')
                    time.sleep(1)
                    st.experimental_rerun()
                st.balloons()
                time.sleep(1)
                st.experimental_rerun()
            else:
                st.error('This role was taken just now, try again.')
                time.sleep(1)
                st.experimental_rerun()
        onclick = st.button(label='Confirm selection')
        if onclick:
            confirm_selection(role_selection,user)
        st.stop()
# with st.expander('Developer tools'):
#     st.dataframe(df_m)


st.title('FRC Game companion WebApp')
st.caption('Developed by Sina Golchi in collaboration with FRC Team under creative commons license')

#sidebar and login system

st.sidebar.write('Please Login below:')
user_name = st.sidebar.text_input('Your unique FRC ID',type='password')
user_roster = get_sql('frc_users')
user_roster.set_index('user',inplace=True)
try:
    st.sidebar.success('Welcome '+ user_roster.loc[user_name,'name'])
except Exception as e:
    print(e)
    if user_name == '':
        st.warning('You are not logged in! Please login from the sidebar on the left.\n'
                   'If sidebar is hidden reveal it via the arrow on the upper left of this page')
        st.stop()
    else:
        st.error('Your unique ID is incorrect, please contact FRC admins for help!')
        st.stop()


with st.sidebar:
    if user_roster.loc[user_name,'level'] > 1:
        board = st.selectbox(label='FRC Board number', options=[1, 2, 3, 4, 5, 6])
        user_id = user_dict_inv[st.selectbox(label='Role', options=user_dict.values())]
    else:
        board = int(user_roster.loc[user_name,'board'])
        user_id = user_roster.loc[user_name,'role']

    df = get_sql('budget_lb' + str(board))
    df.set_index('role', inplace=True)
    df_m = get_sql('measures_lb1')
    df_m.set_index('measure_id', inplace=True)
    df_v = get_sql('frc_long_variables')
    df_v.set_index('board', inplace=True)
    g_round = df_v.loc[board, 'round']

    st.caption('Game round')
    st.info('We are on round '+str(int(df_v.loc[board, 'round'])))
    st.caption('Game phase')
    st.info(phase_dict[df_v.loc[board, 'phase']])
    confirm_rerun = st.button(label='Refresh Data')
    if confirm_rerun:
        refresh()

if user_id == None:
    choose_role(user_name,board)

st.header("Your role is: " + str(user_dict[user_id]) + " on board " + str(board))

other_roles = [x for x in user_dict.keys() if x != user_id]

st.header('Your budget')
st.metric(value='$'+str(df.loc[user_id,'cb']),delta=int(df.loc[user_id,'delta']),label="My Current budget")


with st.expander('Participants budgets'):
    metric_cols_1 = st.columns(7)
    metric_cols_2 = st.columns(7)
    metric_cols_3 = st.columns(7)
    metric_cols = metric_cols_1 + metric_cols_2 + metric_cols_3

    for col, role in zip(metric_cols,other_roles):
        with col:
            st.metric(label=user_dict[role],value='$'+str(df.loc[role,'cb']),delta=int(df.loc[role,'delta']))


#sql queries for bidding
update_bid_measure = ("UPDATE measures_lb1 SET person_bid = %s, total_bid = total_bid + %s WHERE measure_ID=%s;")
update_bid_role =  ("UPDATE budget_lb%s SET r%s_measure = %s, r%s_bid = %s WHERE role=%s;")
log_bid = ("INSERT INTO measure_log%s VALUES (NOW(),%s,%s,%s,%s);")

#sql queries for taxes
update_tax =  ("UPDATE budget_lb%s SET r%s_tax = %s, cb = cb - %s WHERE role=%s;")
update_taxman = ("UPDATE budget_lb%s SET cb = cb + %s WHERE role=%s;")


#SQL queries for budget manipulation
update_budget = ("UPDATE budget_lb%s SET cb = %s WHERE role=%s;")
update_delta =  ("UPDATE budget_lb%s SET delta = %s WHERE role=%s;")
log_transaction = ("INSERT INTO payment%s VALUES (NOW(),%s,%s,%s);")

def tax_increacse_section():
    st.markdown("""___""")

    auth_name_dict = {'PP': 'provincial tax', 'FP': 'federal tax', 'M': 'municipal tax'}
    def tax_increase(authority, increment):
        # sql query for tax increase

        auth_dict = {'PP':'provincial_tax', 'FP':'federal_tax', 'M':'municipal_tax'}
        increase_tax_db = ("UPDATE frc_long_variables SET " + auth_dict[authority] + '=' + auth_dict[authority] +"+ %s WHERE board=%s")

        curA = conn.cursor()
        curA.execute(increase_tax_db,(increment,board))
        conn.commit()
        with st.spinner('Consulting with ministers'):
            time.sleep(2)
        st.success('Tax rate increased :|')
        time.sleep(2)

    if ((user_id == 'PP' or user_id=='M') or user_id =='FP') and g_round != 1:
        st.header("Determine tax rate for this round")
        with st.expander('help'):
            st.markdown(
                '### Tax increase \n This section is reserved for government officials to decide if they want to increase taxt \n'
                'here are some of the rules:\n'
                '- The tax cannot be increased on the first round from the starting one buddget unit per round\n'
                '- The tax rate for each government official can only increase by one unit per round\n'
                '- Be fare while increasing tax, remember that people and organizations can vote in favor or against you at the end of each round')
        st.markdown('You can increase ' +  auth_name_dict[user_id] +' by the amount below:')
        col1 , col2 = st.columns(2)
        with col1:
            increment = st.number_input(label='Increase by', value=0, min_value=0, max_value=2)
        with col2:
            confirm_tax_inc = st.button(label='Confirm tax increase')

        if confirm_tax_inc:
            tax_increase(user_id,increment)

    elif ((user_id == 'PP' or user_id=='M') or user_id =='FP') and g_round == 1:
        st.header("Determine tax rate for this round")
        with st.expander('help'):
            st.markdown(
                '### Tax increase \n This section is reserved for government officials to decide if they want to increase taxt \n'
                'here are some of the rules:\n'
                '- The tax cannot be increased on the first round from the starting one buddget unit per round\n'
                '- The tax rate for each government official can only increase by one unit per round\n'
                '- Be fare while increasing tax, remember that people and organizations can vote in favor or against you at the end of each round')
        st.markdown('The ' + auth_name_dict[user_id] + ' is set to 1 budget unit for the first round \n'
                                                       'you will get a chance to increase it in the next rounds')
    else:
        st.info('We are waiting to hear from our government officials about the tax rate')

def taxes_section():
    st.markdown("""___""")
    auth_name_dict = {'PP': 'provincial tax', 'FP': 'federal tax', 'M': 'municipal tax'}
    def pay_tax(user_id):
        if user_id == 'FN':
            df_v = get_sql('frc_long_variables')
            df_v.set_index('board', inplace=True)
            curA = conn.cursor()
            tax_total = int(df_v.loc[board, 'provincial_tax'])
            curA.execute(update_tax, (int(board),int(g_round), True, tax_total, user_id))
            curA.execute(update_taxman, (int(board),int(df_v.loc[board, 'provincial_tax']), 'PP'))
            conn.commit()
            with st.spinner('Depositing taxes'):
                time.sleep(2)
            st.success('You payed your taxes :)')
            time.sleep(2)
            st.experimental_rerun()

        elif user_id == 'I' or user_id == 'LD' or user_id== 'J' or user_id == 'LEF':
            df_v = get_sql('frc_long_variables')
            df_v.set_index('board', inplace=True)
            curA = conn.cursor()
            tax_total = int(df_v.loc[board, 'provincial_tax'] + df_v.loc[board, 'federal_tax'])
            curA.execute(update_tax, (int(board), int(g_round), True, tax_total, user_id))
            curA.execute(update_taxman, (int(board), int(df_v.loc[board, 'provincial_tax']), 'PP'))
            curA.execute(update_taxman, (int(board), int(df_v.loc[board, 'federal_tax']), 'FP'))
            conn.commit()
            with st.spinner('Depositing taxes'):
                time.sleep(2)
            st.success('You payed your taxes :)')
            time.sleep(2)
            st.experimental_rerun()

        else:
            df_v = get_sql('frc_long_variables')
            df_v.set_index('board', inplace=True)
            curA = conn.cursor()
            tax_total = int(df_v.loc[board,'municipal_tax']+df_v.loc[board,'provincial_tax']+df_v.loc[board,'federal_tax'])
            curA.execute(update_tax,(int(board), int(g_round),True,tax_total,user_id))
            curA.execute(update_taxman, (int(board), int(df_v.loc[board,'municipal_tax']),'M'))
            curA.execute(update_taxman, (int(board), int(df_v.loc[board,'provincial_tax']),'PP'))
            curA.execute(update_taxman, (int(board), int(df_v.loc[board,'federal_tax']),'FP'))
            conn.commit()
            with st.spinner('Depositing taxes'):
                time.sleep(2)
            st.success('You payed your taxes :)')
            time.sleep(2)
            st.experimental_rerun()

    def process_m_p(user,amount,receiving_party):
        curA = conn.cursor()
        curA.execute('UPDATE budget_lb%s SET cb=cb-%s WHERE role=%s',(int(board),amount,user))
        curA.execute('UPDATE budget_lb%s SET cb=cb+%s WHERE role=%s',(int(board),amount,receiving_party))
        conn.commit()
        with st.spinner('processing payment to ' + receiving_party):
            time.sleep(1)
        st.success('Payment processed')

    def process_m_c(user,amount):
        curA = conn.cursor()
        curA.execute('UPDATE budget_lb%s SET cb=cb-%s WHERE role=%s',(int(board),amount,user))
        conn.commit()
        with st.spinner('processing payment for the cost'):
            time.sleep(1)
        st.success('Payment processed')

    def set_as_paid(user):
        curA = conn.cursor()
        curA.execute('UPDATE budget_lb%s SET r%s_m_payment=%s WHERE role=%s',(int(board),int(g_round),True,user))
        conn.commit()
        st.success('All payments were successful! :)')
        time.sleep(1)
        st.experimental_rerun()

    if  user_id == 'M' or user_id == 'PP' or user_id == 'FP' or user_id == 'EM' or user_id == 'DP' or user_id == 'PH' or user_id == 'TA' or user_id == 'WW' or user_id == 'EM':
        st.header('Taxes')
        st.info('You are not obligated to pay taxes')


    elif user_id == 'FN':
        st.header('Taxes')
        if not df.loc[user_id,'r' + str(g_round) + '_tax']:
            st.markdown('Please settle your taxes before going forward')
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label='Provincial tax', value=int(df_v.loc[board, 'provincial_tax']))
            with col2:
                tax = st.button(label='Pay taxes')

            if tax:
                pay_tax(user_id)
        else:
            st.success('Your taxes are settled for this round')

    elif user_id == 'I' or user_id == 'J' or user_id == 'LD' or user_id == 'LEF':
        st.header('Taxes')
        if not df.loc[user_id, 'r' + str(g_round) + '_tax']:
            st.markdown('Please settle your taxes before going forward')
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label='Provincial tax', value=int(df_v.loc[board, 'provincial_tax']))
            with col2:
                st.metric(label='Federal_tax', value=int(df_v.loc[board, 'federal_tax']))
            with col3:
                tax = st.button(label='Pay taxes')

            if tax:
                pay_tax(user_id)
        else:
            st.success('Your taxes are settled for this round')

    else:
        st.header('Taxes')
        if not df.loc[user_id, 'r' + str(g_round) + '_tax']:
            st.markdown('Please settle your taxes before going forward')
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label='Municipal tax', value=int(df_v.loc[board, 'municipal_tax']))
            with col2:
                st.metric(label='Provincial tax', value=int(df_v.loc[board, 'provincial_tax']))
            with col3:
                st.metric(label='Federal_tax', value=int(df_v.loc[board, 'federal_tax']))

            tax = st.button(label='Pay taxes')
            if tax:
                pay_tax(user_id)
        else:
            st.success('Your taxes are settled for this round')

    st.markdown('''---''')
    st.subheader('Additional mandatory payments')

    if df.loc[user_id,'r'+str(g_round)+'_m_payment']:
        st.success('your mandatory payments are settled for this round')

    else:
        if user_id == 'DP' or user_id == 'EM' or user_id == 'PH':
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label='Utility', value=int(df_v.loc[board, 'power_price']))
            with col2:
                st.metric(label='Cost of running the department', value=2)

            confirm_m_payment = st.button(label='Process mandatory payments')
            if confirm_m_payment:
                process_m_p(user_id, int(df_v.loc[board, 'power_price']),'PUC')
                process_m_c(user_id, 2)
                set_as_paid(user_id)


        elif user_id == 'ENGO':
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label='Utility', value=int(df_v.loc[board, 'power_price']))
            with col2:
                st.metric(label='Cost of running the department', value=1)

            confirm_m_payment = st.button(label='Process mandatory payments')
            if confirm_m_payment:
                process_m_p(user_id, int(df_v.loc[board, 'power_price']), 'PUC')
                process_m_c(user_id, 1)
                set_as_paid(user_id)

        elif user_id == 'FP':
            st.metric(label='Cost of running the government',value=15)
            confirm_m_payment = st.button(label='Process mandatory payments')
            if confirm_m_payment:
                process_m_c(user_id, 15)
                set_as_paid(user_id)
            st.subheader('Occasional costs')
            st.info('You are required to provide additional funding to First Nations if they exprience a flood')
            st.info(
                'You are required to provide funding (DFAA) to provincial govenrment, so that the province can pay flood victims DRP')

        elif user_id == 'I':
            st.info(
                'You should not spend more than 3/4 of your initial budget per round on FRM measures and keep 1/4 in reserve')

        elif user_id == 'J':
            st.info('There is no additional cost to your role')

        elif user_id == 'LD':
            st.metric(label='Mandatory payement to medium value residents (CRA-MV)', value=2)

            confirm_m_payment = st.button(label='Process mandatory payments')
            if confirm_m_payment:
                process_m_p(user_id, 2, 'CRA-MV')
                set_as_paid(user_id)

        elif user_id == 'LEF':
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label='Utility', value=int(df_v.loc[board, 'power_price']))
            with col2:
                st.metric(label='Mandatory payment to high value residents (CRA-HV)', value=3)

            confirm_m_payment = st.button(label='Process mandatory payments')
            if confirm_m_payment:
                process_m_p(user_id, int(df_v.loc[board, 'power_price']), 'PUC')
                process_m_p(user_id, 3, 'CRA-HV')
                set_as_paid(user_id)

            st.subheader('Occasional costs')
            st.info('You must pay 2 budget units to ENGO for compensation per each structural measure')

        elif user_id == 'LBO':
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label='Utility', value=int(df_v.loc[board, 'power_price']))
            with col2:
                st.metric(label='Mandatory payment to mobile home residents (CRA-MHA)', value=1)
            confirm_m_payment = st.button(label='Process mandatory payments')
            if confirm_m_payment:
                process_m_p(user_id, int(df_v.loc[board, 'power_price']), 'PUC')
                process_m_p(user_id, 1, 'CRA-MHA')
                set_as_paid(user_id)

        elif user_id == 'M':
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(label='Utility', value=int(df_v.loc[board, 'power_price']))
            with col2:
                st.metric(label='Cost of running the government', value=1)
            with col3:
                st.metric(label='Cost of running treatment facilities', value=2)
            with col4:
                st.metric(label='Cost of running emergency services', value=2)

            confirm_m_payment = st.button(label='Process mandatory payments')
            if confirm_m_payment:
                process_m_p(user_id, int(df_v.loc[board, 'power_price']), 'PUC')
                process_m_c(user_id, 1)
                process_m_p(user_id, 2, 'WW')
                process_m_p(user_id, 2, 'EM')
                set_as_paid(user_id)

        elif user_id == 'PUC':
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label='Cost of maintaining the substations',value=2)
            with col2:
                st.metric(label='Cost of running the company', value=2)

            confirm_m_payment = st.button(label='Process mandatory payments')
            if confirm_m_payment:
                process_m_c(user_id, 2)
                process_m_c(user_id, 2)
                set_as_paid(user_id)

        elif user_id == 'PP':
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label='Cost of running the government',value=6)
            with col2:
                st.metric(label='Mandatory payment to hydrologist',value=2)
            with col3:
                st.metric(label='Mandetory payment to transport authority', value=2)

            confirm_m_payment = st.button(label='Process mandatory payments')
            if confirm_m_payment:
                process_m_c(user_id, 6)
                process_m_p(user_id, 2,'PH')
                process_m_p(user_id,2,'TA')
                set_as_paid(user_id)

        elif user_id == 'TA':
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label='Cost of running the department', value=2)
            with col2:
                st.metric(label='Mandatory payment to engineering firm for maintenance', value=1)

            confirm_m_payment = st.button(label='Process mandatory payments')
            if confirm_m_payment:
                process_m_c(user_id, 2)
                process_m_p(user_id, 1, 'LEF')
                set_as_paid(user_id)

        elif user_id == 'WW':
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label='Cost of running the department', value=2)
            with col2:
                st.metric(label='Mandatory payment to engineering firm for maintenance', value=2)

            confirm_m_payment = st.button(label='Process mandatory payments')
            if confirm_m_payment:
                process_m_c(user_id, 2)
                process_m_p(user_id, 2, 'LEF')
                set_as_paid(user_id)

        else:
            st.metric(label='Utility', value=int(df_v.loc[board, 'power_price']))
            confirm_m_payment = st.button(label='Process mandatory payments')
            if confirm_m_payment:
                process_m_p(user_id, int(df_v.loc[board, 'power_price']), 'PUC')
                set_as_paid(user_id)

def tax_section_short():
    st.markdown("""___""")
    st.info('Tax payements are processed automatically')


def bidding_section():
    st.markdown("""___""")
    def make_bid_func(measure, amount):
        df = get_sql('budget_lb' + str(int(board)))
        df.set_index('role',inplace=True)
        bid_total = sum([int(i) for i in df[df['r' + str(g_round) + '_measure'] == measure][
                        'r' + str(g_round) + '_bid'].to_list()])
        if measure in df['r' + str(g_round) + '_measure'].to_list() and bid_total + amount > df_m.loc[measure,'cost']:

            st.error('The amount you are bidding will increase the total bid ve the cost of measure, consider changing your bid to ' + str(int(df_m.loc[measure,'cost']-bid_total)) +
                     ' or less, or alternatively bid on a different measure')
            time.sleep(3)
            st.experimental_rerun()

        else:
            cur = conn.cursor()
            cur.execute(update_bid_role,(int(board),int(g_round),measure,int(g_round),amount,user_id))
            cur.execute(update_bid_measure, (user_id, amount, measure))
            if df.loc[user_id,'r1_measure'] == None:
                cur.execute(log_bid,(int(board),'New',user_dict[user_id],amount,measure))
            else:
                cur.execute(log_bid,(int(board),'Change', user_dict[user_id], amount, measure))
            conn.commit()
            with st.spinner('Registering your bid'):
                time.sleep(3)
            st.success('You bid on ' + measure + ' successfully')
            time.sleep(2)
            st.experimental_rerun()


    #st.header('Phase 1: FRM Measures Bidding')
    st.markdown('<p style="font-size: 40px; color:rgb(58, 134, 255);">Phase 1: FRM Measures Bidding</p>', unsafe_allow_html=True)
    col1_f, col2_f, col3_f = st.columns(3)

    with col1_f:
        mit_type = st.radio(label='Type of mitigation', options=['Structural','Natural', 'Social'])
        bid_measure = st.selectbox(label='Measures', options=list(df_m[df_m['type']==mit_type].index.values))
    with col2_f:
        if int(df_m.loc[bid_measure, 'cost']) != 0:
            st.metric(label='Cost of ' + bid_measure, value=int(df_m.loc[bid_measure, 'cost']))
            bid_amount = int(st.selectbox(label='how much you would like to bid?', options=[x for x in range(1,11)]))

            with col3_f:
                st.metric(label='Your budget if bid successful', value=int(df.loc[user_id, 'cb'] - bid_amount), delta=-bid_amount)
                make_bid = st.button("Make/Change the bid")

            if make_bid:
                make_bid_func(bid_measure, bid_amount)
        else:
            st.markdown('### The cost is covered by taxes')



    st.subheader('Measures suggested')
    for measure in df_m.index.values:
        if measure in df['r' + str(g_round) + '_measure'].to_list():
            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric(label=measure, value=str(sum([int(i) for i in df[df['r' + str(g_round) + '_measure'] == measure][
                    'r' + str(g_round) + '_bid'].to_list()])) + r"/" + str(int(df_m.loc[measure, 'cost'])))
            with col2:
                biders = list(df[df['r' + str(g_round) + '_measure'] == measure].index)
                amounts = df[df['r' + str(g_round) + '_measure'] == measure]['r' + str(g_round) + '_bid'].to_list()
                st.caption('Bidders: ' + ',  '.join([user_dict[p] + ': \$' + str(b) for p, b in zip(biders, amounts)]))
                try:
                    st.progress(int(sum([int(i) for i in df[df['r' + str(g_round) + '_measure'] == measure][
                        'r' + str(g_round) + '_bid'].to_list()]) / df_m.loc[measure, 'cost'] * 100))
                except:
                    st.warning('The bid on this measure have exceeded the cost, please readjust bids')

    df_impl_measures = get_sql('impl_measures'+str(board))
    st.subheader('Implemented measures')
    for m_row in df_impl_measures.iterrows():
        m_row = m_row[1]
        if m_row['round'] == g_round:
            col1, col2,col3 = st.columns([1,3,1])
            with col1:
                st.metric(label=m_row['measure'],
                              value=str(sum(m_row['amounts'])) + r"/" + str(
                                  int(df_m.loc[m_row['measure'], 'cost'])))
            with col2:
                st.caption(
                    'Bidders: ' + ',  '.join([user_dict[p] + ': \$' + str(b) for p, b in zip(m_row['biders'], m_row['amounts'])]))

                st.progress(int(sum(m_row['amounts']) / df_m.loc[m_row['measure'], 'cost'] * 100))
            with col3:
                st.success('Implemented')

    confirm_rerun = st.button(label='Refresh Data',key='bidding section')
    if confirm_rerun:
        refresh()


def transaction_section():
    st.markdown("""___""")

    def money_transfer(amount,r_party):
        curA = conn.cursor()
        curA.execute(update_budget,(int(board), int(df.loc[user_id,'cb'])-amount,user_id))
        curA.execute(update_delta,(int(board), -amount,user_id))
        curA.execute(update_budget,(int(board), int(df.loc[r_party,'cb']+amount),r_party))
        curA.execute(update_delta,(int(board), +amount,r_party))
        curA.execute(log_transaction,(int(board) ,user_dict[user_id],amount,user_dict[r_party]))
        conn.commit()


    st.header("Phase 1B: Transactions")
    col1 , col2, col3, col4 = st.columns(4)
    with col1:
        t_amount = int(st.selectbox(label='Budget to transfer',options=[x for x in range(1,10)]))
    with col2:
        party = user_dict_inv[st.selectbox(options=[user_dict[x] for x in other_roles], label='Stakeholder receiving')]
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


    st.subheader('Measures suggested')
    for measure in df_m.index.values:
        if measure in df['r' + str(g_round) + '_measure'].to_list():
            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric(label=measure,
                          value=str(sum([int(i) for i in df[df['r' + str(g_round) + '_measure'] == measure][
                              'r' + str(g_round) + '_bid'].to_list()])) + r"/" + str(int(df_m.loc[measure, 'cost'])))
            with col2:
                biders = list(df[df['r' + str(g_round) + '_measure'] == measure].index)
                amounts = df[df['r' + str(g_round) + '_measure'] == measure]['r' + str(g_round) + '_bid'].to_list()
                st.caption('Bidders: ' + ',  '.join([user_dict[p] + ': $' + str(b) for p, b in zip(biders, amounts)]))
                try:
                    st.progress(int(sum([int(i) for i in df[df['r' + str(g_round) + '_measure'] == measure][
                        'r' + str(g_round) + '_bid'].to_list()]) / df_m.loc[measure, 'cost'] * 100))
                except:
                    st.warning('The bid on this measure have exceeded the cost')
    confirm_rerun = st.button(label='Refresh Data', key='bidding section')
    if confirm_rerun:
        refresh()

    st.header('Summary')
    with st.expander("Bidding summary"):
        df_m_log = get_sql('measure_log' + str(board))
        est = pytz.timezone('EST')
        df_m_log = df_m_log.rename(
            columns={'datetime': 'Timestamp', 'bid_type': 'Type of bid', 'person_biding': 'Role of bidder',
                     'amount': 'Amount of bid', 'measure': 'Measure'})
        if not df_m_log.empty:
            df_m_log['Timestamp'] = df_m_log['Timestamp'].dt.tz_convert('EST').dt.strftime('%B %d, %Y, %r')
            st.dataframe(df_m_log)

    with st.expander("Transaction summary"):
        df_p_log = get_sql('payment' + str(board))
        est = pytz.timezone('EST')
        df_p_log = df_p_log.rename(
            columns={'datetime': 'Timestamp', 'from_user': 'Sender', 'amount': 'Transaction total',
                     'to_user': 'Receiving party'})
        df_p_log['id'] = [int(p) for p in df_p_log['id']]
        df_p_log.set_index('id', inplace=True)
        if not df_p_log.empty:
            df_p_log['Timestamp'] = df_p_log['Timestamp'].dt.tz_convert('EST').dt.strftime('%B %d, %Y, %r')
            st.dataframe(df_p_log)

#Transactions for short version
def transactions_short():
    def money_transfer(amount, r_party):
        curA = conn.cursor()
        curA.execute(update_budget, (int(board), int(df.loc[user_id, 'cb']) - amount, user_id))
        curA.execute(update_delta, (int(board), -amount, user_id))
        curA.execute(update_budget, (int(board), int(df.loc[r_party, 'cb'] + amount), r_party))
        curA.execute(update_delta, (int(board), +amount, r_party))
        curA.execute(log_transaction, (int(board), user_dict[user_id], amount, user_dict[r_party]))
        conn.commit()

    st.header("Secret Transactions")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        t_amount = int(st.selectbox(label='Budget to transfer', options=[x for x in range(1, 10)]))
    with col2:
        party = user_dict_inv[
            st.selectbox(options=[user_dict[x] for x in other_roles], label='Stakeholder receiving')]
    with col4:
        transfer = st.button(label='Complete transaction', help='Only click when you are absolutely sure')
    with col3:
        st.metric(label='Budget after transaction', value='$' + str(df.loc[user_id, 'cb'] - t_amount),
                  delta=-t_amount)

    if transfer:
        money_transfer(t_amount, party)
        with st.spinner('Performing transaction'):
            time.sleep(3)
        st.success('The transaction to ' + party + ' was successful')
        time.sleep(3)
        st.experimental_rerun()

    def styler(val):
        color = 'green' if val == user_dict[user_id] else 'blue'
        return 'color: %s' % color

    st.subheader('History')
    st.caption("Only transaction relating to you will show up here")
    df_p_log = get_sql('payment' + str(board))
    est = pytz.timezone('EST')
    df_p_log = df_p_log.rename(
        columns={'datetime': 'Timestamp', 'from_user': 'Sender', 'amount': 'Transaction total',
                 'to_user': 'Receiving party'})
    df_p_log['id'] = [int(p) for p in df_p_log['id']]
    df_p_log.set_index('id', inplace=True)
    #df_pesonalized = df_p_log[df_p_log['Sender']==user_dict_inv[user_id] or df_p_log['Receiving party']==user_dict_inv[user_id]]
    if not df_p_log.empty:
        df_p_log['Timestamp'] = df_p_log['Timestamp'].dt.tz_convert('EST').dt.strftime('%B %d, %Y, %r')
        df_pesonalized = df_p_log[(df_p_log['Sender'] == user_dict[user_id]) | (df_p_log['Receiving party'] == user_dict[user_id])]
        df_pesonalized = df_pesonalized.style.applymap(styler)
        st.dataframe(df_pesonalized)
    else:
        st.info("No transaction to show")
#Voting section

update_vote_DB = ("UPDATE budget_lb%s SET r%s_vote=ARRAY[%s,%s,%s] WHERE role=%s;")
vote_override = df_v.loc[board,'r'+str(g_round)+'_vote_override']

def voting():
    df = get_sql('budget_lb' + str(board))
    df.set_index('role',inplace=True)
    st.header('Round ' + str(g_round) + ' vote of confidence')
    if df.loc[user_id,'r'+str(g_round)+'_vote'] is None:
        def submit_vote(results, user):
            curA = conn.cursor()
            curA.execute(update_vote_DB, (int(board),int(g_round), *results, user))
            conn.commit()
            with st.spinner('submitting your vote'):
                time.sleep(2)
            st.success('Your vote is submitted, awaiting results')


        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown('Mayor')
            M_vote = st.radio(key='M_vote',label='Your vote',options=['In Favor','Against'])
        with col2:
            st.markdown('Provincial Politician')
            PP_vote = st.radio(key='PP_vote',label='Your vote',options=['In Favor','Against'])
        with col3:
            st.markdown('Federal Politician')
            FP_vote = st.radio(key='FP_vote',label='Your vote',options=['In Favor','Against'])
        with col4:
            approve_vote = st.button(label='submit your vote')

        if approve_vote:
            submit_vote([M_vote,PP_vote,FP_vote],user_id)


    elif not [i for i in df.loc[:,'r'+str(g_round)+'_vote'] if i == None] or vote_override:
        vote = []
        vote_g_round = []
        official = []
        for r in range(1,4):
            for v in df.loc[:,'r'+str(r)+'_vote']:
                if v is not None:
                    for i, o in zip(range(3),['Mayor','Provincial politician','Federal politician']):
                        vote.append(v[i])
                        official.append(o)
                        vote_g_round.append(r)
        df_vote_result = pd.DataFrame(zip(vote,official,vote_g_round),columns=['Votes','Official','Game round'])
        sns.set_theme(style='darkgrid',palette='colorblind')
        fig = sns.catplot(data=df_vote_result,x='Votes',col='Official',kind='count',row='Game round')
        st.pyplot(fig)

    else:
        st.info('Awaiting results')

def vote_short():
    df = get_sql('budget_lb' + str(board))
    df.set_index('role',inplace=True)
    st.header('Round ' + str(g_round) + ' vote of confidence')
    if df.loc[user_id,'r'+str(g_round)+'_vote'] is None:
        def submit_vote(results, user):
            curA = conn.cursor()
            curA.execute("UPDATE budget_lb%s SET r%s_vote=ARRAY[%s] WHERE role=%s;", (int(board),int(g_round), *results, user))
            conn.commit()
            with st.spinner('submitting your vote'):
                time.sleep(1)
            st.success('Your vote is submitted, awaiting results')


        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown('Mayor')
            M_vote = st.radio(key='M_vote',label='Your vote',options=['In Favor','Against'])
        with col2:
            approve_vote = st.button(label='submit your vote')

        if approve_vote:
            submit_vote([M_vote],user_id)


    elif not [i for i in df.loc[:,'r'+str(g_round)+'_vote'] if i == None] or vote_override:
        vote = []
        vote_g_round = []
        official = []
        for r in range(1,4):
            for v in df.loc[:,'r'+str(r)+'_vote']:
                if v is not None:
                    for i, o in zip(range(1),['Mayor']):
                        vote.append(v[i])
                        official.append(o)
                        vote_g_round.append(r)
        df_vote_result = pd.DataFrame(zip(vote,official,vote_g_round),columns=['Votes','Official','Game round'])
        sns.set_theme(style='darkgrid',palette='colorblind')
        fig = sns.catplot(data=df_vote_result,x='Votes',col='Official',kind='count',row='Game round',size=5,aspect=2)
        st.pyplot(fig)

    else:
        st.info('Awaiting results')


def flood():
    qulified_for_DRP = ['CRA-HV','CRA-MV','CRA-MHA','ENGO','F']
    st.markdown('''___''')
    st.header('Flood event')
    st.info(str(df_v.loc[board,'floods'][g_round-1]) + ' is in effect')
    st.subheader('Damage analysis')
    if df.loc[user_id,'r'+str(g_round) +'_flood'] is not None:
        st.warning('You are affected by the flood')
        if df.loc[user_id,'r'+str(g_round) +'_flood'][1]:
            st.success('You were protected by the measures in place')
        else:
            st.warning('You were not protected by the measures in place')
            st.info('The total cost of damage to your property is: $' + str(df.loc[user_id,'r'+str(g_round) +'_flood'][2]))
            if not df.loc[user_id,'r'+str(g_round)+'_insurance']:
                st.warning('Unfortunately, you were not insured for this round')
                if user_id in qulified_for_DRP:
                    st.success('You are eligible for DRP rebate of upto 3 budget units, The admin will process your claim')
                else:
                    st.warning('Unfortunately you are not eligible for DRP')
            else:
                st.success('You were insured for this round, you will receive 3/4 of the total damge. The admin will process your claim')

    else:
        st.success('You are not affected by the flood')


#dict_phase_case = {0:tax_increacse_section ,1:tax_section_short, 2: bidding_section, 3:transaction_section, 4:flood, 5:voting}
dict_phase_case = {0:None , 1: bidding_section, 2:flood, 3:tax_section_short, 4:voting}

#### Practice version
if df_v.loc[board,'practice']:
    def progress_game(direction):
        prog_counter = int(df_v.loc[board, 'prog_counter'])
        dict_prog = {0: [1, 1], 1: [1, 2], 2: [1, 3], 3: [1, 4], 4: [2, 1], 5: [2, 2], 6: [2, 3], 7: [2, 4], 8: [3, 1],
                     9: [3, 2], 10: [3, 3], 11: [3, 4]}
        if direction == 'forward':
            prog_counter += 1
        else:
            prog_counter -= 1
        curA = conn.cursor()
        curA.execute("UPDATE frc_long_variables SET phase=%s WHERE board=%s", (dict_prog[prog_counter][1], board))
        curA.execute("UPDATE frc_long_variables SET round=%s WHERE board=%s", (dict_prog[prog_counter][0], board))
        conn.commit()
        curA = conn.cursor()
        curA.execute("UPDATE frc_long_variables SET prog_counter=%s WHERE board=%s", (prog_counter, board))
        conn.commit()
        st.success('We progressed to next phase!')


    set_phase = int(df_v.loc[board, 'phase'])
    prog_counter = int(df_v.loc[board, 'prog_counter'])
    with st.sidebar:
        st.warning('Practice mode is enabled, use buttons below to progress game')
        colu1, colu2 = st.columns(2)

        with colu1:
            st.button(label='Return', on_click=progress_game, kwargs={'direction': 'return'},
                      help='Click here to go back to the last stage', disabled=prog_counter == 0)

        with colu2:
            st.button(label='Progress game', on_click=progress_game, kwargs={'direction': 'forward'},
                      help='Click here to progress to next stage', disabled=prog_counter == 11)

if dict_phase_case[df_v.loc[board,'phase']] is not None:
    dict_phase_case[df_v.loc[board,'phase']]()

if user_id == 'PH':
    with st.expander('Possible flood maps'):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.image('imgs/Convective summer storm.png')
            st.image('imgs/Freshet spring flooding.png')
        with col2:
            st.image('imgs/Ice-jams-winter-flodding.png')
            st.image('imgs/Minor localized flooding (1).png')
        with col3:
            st.image('imgs/SLR test.png')
            st.image('imgs/Storm surge winter flooding.png')

if game_type == 'Simplified' or game_type == 'full':
    st.markdown("""___""")
    with st.expander('Secret transactions'):
        transactions_short()

#function for buying insurance
insurance_update = ("UPDATE budget_lb%s SET r%s_insurance = %s WHERE role=%s;")
def insure_me(board,user, action):
    cur = conn.cursor()
    cur.execute(insurance_update,(int(board),int(g_round),action,user))
    if action:
        cur.execute(update_budget, (int(board), int(df.loc[user_id, 'cb']) - int(df_v.loc[board,'insurance_price']), user_id))
        cur.execute(update_delta, (int(board), -int(df_v.loc[board,'insurance_price']), user_id))
        conn.commit()
        with st.spinner('Preparing your policy'):
            time.sleep(2)
        st.success('You are insured :)')
        time.sleep(2)
        st.experimental_rerun()
    else:
        cur.execute(update_budget, (int(board), int(df.loc[user_id, 'cb']) + int(df_v.loc[board,'insurance_price']), user_id))
        cur.execute(update_delta, (int(board), +int(df_v.loc[board,'insurance_price']), user_id))
        conn.commit()
        with st.spinner('Cancelling your policy'):
            time.sleep(2)
        st.success('Your policy was canceled successfully')
        time.sleep(2)
        st.experimental_rerun()



#Insurance section sidebar

with st.sidebar:
    st.markdown("""___""")
    if int(df_v.loc[board, 'phase']) <= 3:
        if user_id =='I':
            st.header('Insurance deals')
            slogan = st.text_input(label='Set your slogan for selling insurance', value=df_v.loc[board,'insurance_slogan'])
            col1, col2 = st.columns(2)
            with col1:
                insurance_price = st.number_input(label='insurance price',value=df_v.loc[board,'insurance_price'])
            with col2:
                st.metric(label='Current Price', value=int(df_v.loc[board,'insurance_price']))

            def set_insure_price():
                curA = conn.cursor()
                curA.execute("UPDATE frc_long_variables SET insurance_slogan = %s, insurance_price = %s WHERE board= %s",(slogan,int(insurance_price),int(board)))
                conn.commit()
                with st.spinner('annoy people with insurance ads on YouTube'):
                    time.sleep(2)
                st.success('Insurance info updated')

            insure_change = st.button('Confirm changes', key='Insurance_change_confirm')
            if insure_change:
                set_insure_price()

        else:
            st.header('Flood insurance')
            if not df.loc[user_id,'r'+str(g_round)+'_insurance']:
                st.warning('You are not insured for round ' + str(g_round))
                st.subheader('Would you like to purchase insurance?')
                st.caption('Insurance company advertisement:')
                st.info(df_v.loc[board,'insurance_slogan'])

                col1, col2 = st.columns(2)
                with col1:
                    insure = st.button(label='Buy insurance')
                with col2:
                    st.metric(label='Budget preview', value=int(df.loc[user_id,'cb']-int(df_v.loc[board,'insurance_price'])),delta=-int(df_v.loc[board,'insurance_price']))
                if insure:
                    insure_me(board,user_id, True)
            else:
                st.success('your property is insured for round ' + str(g_round))
                cancel_policy = st.button(label='Cancel policy')
                if cancel_policy:
                    insure_me(board,user_id,False)
    else:
        if not df.loc[user_id, 'r' + str(g_round) + '_insurance']:
            st.warning('You are not insured for round ' + str(g_round))
            st.info('You can no longer purchase insurance for this round')
        else:
            st.success('your property is insured for round ' + str(g_round))
            st.info('You can no longer cancel your insurance for this round')

st.markdown('''---''')
st.subheader('Miro board ' + str(int(board)))
miro_dict = {1:['https://miro.com/app/live-embed/uXjVP5Rnvd8=/?moveToViewport=-1278,-7444,8403,5935&embedId=143045527681&embedAutoplay=true','https://miro.com/app/board/uXjVP5Rnvd8=/?share_link_id=424657725671'],
             2:['https://miro.com/app/live-embed/uXjVP5RnvfU=/?moveToViewport=-1096,-7622,8193,6241&embedId=384110064484&embedAutoplay=true','https://miro.com/app/board/uXjVP5RnvfU=/?share_link_id=17892545068'],
             3:['https://miro.com/app/live-embed/uXjVPBmsTmg=/?moveToViewport=-10463,-6096,8785,4266&embedId=26206919528&embedAutoplay=true','https://miro.com/app/board/uXjVPBmsTmg=/?share_link_id=27320976313'],
             4:['https://miro.com/app/live-embed/uXjVOR_hQ8o=/?moveToViewport=-23351,-9416,27515,14305&embedAutoplay=true','https://miro.com/app/board/uXjVOR_hQ8o=/?invite_link_id=471512594109'],
             5:['https://miro.com/app/live-embed/uXjVOR_h058=/?moveToViewport=-23351,-9416,27515,14305&embedAutoplay=true','https://miro.com/app/board/uXjVOR_h058=/?invite_link_id=575464384272'],
             6:['https://miro.com/app/live-embed/uXjVOR_h1vw=/?moveToViewport=-23351,-9416,27515,14305&embedAutoplay=true','https://miro.com/app/board/uXjVOR_h1vw=/?invite_link_id=87971323805']}

with st.expander('Miro board', expanded=True):
    components.iframe(miro_dict[int(board)][0],height=700,scrolling=False)

    st.write("Open board in a new tab [link]("+miro_dict[int(board)][1]+')')