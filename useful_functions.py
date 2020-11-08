# ------------------------------------Import Libraries-----------------------------------------

def global_import(modulename, shortname=None):

  modulename = modulename.strip()

  if shortname is None:
    shortname = modulename.split('.')[-1]

  if '.' in modulename:
    if modulename.count('.') > 1:
      print('Too complicated, cannot handle now.')
      return 1

    top_level_module = modulename.split('.')[0]

    globals()[top_level_module] = __import__(top_level_module)
    globals()[shortname] = eval(modulename)
    return 0

  else:
    globals()[shortname] = __import__(modulename)
    return 0


def import_libraries():
  global_import('warnings')
  warnings.simplefilter(action='ignore', category=FutureWarning)
  global_import('pandas', 'pd')
  global_import('numpy', 'np')
  global_import('seaborn', 'sns')
  global_import('matplotlib.pyplot', 'plt')
  # global_import('statsmodels.api', 'sm') # AttributeError: module 'statsmodels' has no attribute 'api'
  # global_import('patsy')
  # global_import('sklearn')
  global_import('re')
  pd.set_option('display.max_columns', 100)
  pd.set_option('display.max_rows', 100)
  global default_dpi
  default_dpi = 90
  print('Importing Done')


# -------------------------------------Data Selection----------------------------------------------


def load_data(which_year):
  '''Provide the census year you will to load (choose from 1850, 1880, 1910)'''
  try:
    df = pd.read_csv('/content/drive/My Drive/census_' + str(which_year) + '.csv', low_memory=False)
    return df
  except FileNotFoundError as e:
    print('File Not Found! Please check if you have created Shortcuts for the data files\nin your "My Drive" folder and if you have run the first cell in this notebook.\nLink to the data folder: https://drive.google.com/drive/folders/19dZe5h63fdCYNnW421woQv4Z09QABjam')
  except NameError as e:
    print('Function not defined yet! Please check if you have run the first cell in this notebook.')


def check_parenthesis_and_replace_comma_within_parenthesis(string):

  output = []
  letters = list(string.strip())
  waiting_to_close = False
  while len(letters) > 0:
    head = letters.pop(0)
    if head == '[':
      if waiting_to_close == False:
        waiting_to_close = True
      else:
        return False
    elif head == ']':
      if waiting_to_close == True:
        waiting_to_close = False
      else:
        return False

    if (head == ',' or head == ':') and waiting_to_close == True:
      output.append('|')
    else:
      output.append(head)

  if waiting_to_close == False:
    return ''.join(output)
  else:
    return False

def replace_first_occurence_of_sign(string, sign, replacement):

  first_position_of_sign = string.index(sign)
  new_string = string[:first_position_of_sign] + replacement + string[first_position_of_sign + len(sign):]
  return new_string

def check_for_criteria_type(string, data, sign, alternative_sign, valid_cols):

  sign = ' ' + sign.strip() + ' '
  alternative_sign = ' ' + alternative_sign.strip() + ' '
  left_side_of_sign_or_alt_sign_is_valid_col = ((string.split(sign, maxsplit=1)[0].strip() in valid_cols) or (string.split(alternative_sign, maxsplit=1)[0].strip() in valid_cols))
  if (sign in string or alternative_sign in string) and left_side_of_sign_or_alt_sign_is_valid_col:
    string = replace_first_occurence_of_sign(string, sign, alternative_sign)
    col = string.split(alternative_sign.strip())[0].strip()
    value = string.split(alternative_sign.strip())[1].strip()
    if sign == ' is in ' or sign == ' is not in ':
      try:
        assert(value[0] == '[' and value[-1] == ']')
      except:
        print('value', value)
      value = [option.strip() for option in value[1:-1].split('|')]
    else:
      value = float(value) if value.isnumeric() else value
    return build_criteria(col, value, data, sign=sign)
  else:
    return None

def build_criteria_from_string(string, data):

  valid_cols = data.columns.tolist()

  criteria = check_for_criteria_type(string, data, ' is not in ', ' is not in ', valid_cols)
  if isinstance(criteria, pd.Series):
    return criteria

  criteria = check_for_criteria_type(string, data, ' is not ', ' != ', valid_cols)
  if isinstance(criteria, pd.Series):
    return criteria

  criteria = check_for_criteria_type(string, data, ' is in ', ' is in ', valid_cols)
  if isinstance(criteria, pd.Series):
    return criteria

  criteria = check_for_criteria_type(string, data, ' is ', ' = ', valid_cols)
  if isinstance(criteria, pd.Series):
    return criteria


def build_criteria(col, value, data, sign=' is '):

  if sign == ' is ' or sign == ' is not ':
    output = data[col] == value

  elif sign == ' is in ' or sign == ' is not in ':

    if pd.api.types.is_numeric_dtype(data[col].dtype) and len(value) == 2:
      output = (data[col] >= float(value[0])) & (data[col] < float(value[1]))
    else:
      output = data[col].isin(value)

  if ' not ' in sign:
    output = ~output

  return output


def get_multiple_criteria(string, data):
  if ' is in ' in string:
    string = check_parenthesis_and_replace_comma_within_parenthesis(string)
  multiple_criteria = [c.strip() for c in string.split(',')]
  multiple_criteria = [c + ' = 1' if (' = ' not in c) and (' is ' not in c) and (c in data.columns) else c for c in multiple_criteria]
  multiple_criteria_filters = [build_criteria_from_string(c, data) for c in multiple_criteria]
  combined_filter = pd.Series([True] * len(data))
  for filter in multiple_criteria_filters:
    combined_filter = combined_filter & filter
  return combined_filter


def select_data(criteria_string, data):
  '''Provide a comma separated criteria_string, and specify which dataframe (df) to select from'''
  data = data.reset_index(drop=True).copy()
  criteria_filter = get_multiple_criteria(criteria_string, data)
  return data[criteria_filter].copy()

# -------------------------------------Smart Data Description-------------------------------------------

def describe(col, data, top_k=-1, thres=90, return_full=False, plot_top_k=-1, plot_type='', bins=-1):

  if data[col].isnull().mean() > 0:
    print(f"Notice: {np.round(data[col].isnull().mean()*100,3)}% of the entries have no records for this field.\n")

  data_numeric_columns = data.dtypes[data.dtypes.apply(lambda x: np.issubdtype(x, np.number))].index.tolist()

  if col in data_numeric_columns:
    if bins == -1:
      print(f'Change the default width of histogram bars by setting "bins = <a number>".\n')
      bins = 50
    plt.figure(figsize=(9, 6), dpi=default_dpi)
    plt.hist(data[col].dropna(), bins=bins)
    plt.title(f"Distribution of the {col}")
    basic_stats = data[col].dropna().describe().reset_index()
    basic_stats.columns = ['Field', 'Value']
    basic_stats.Field = ['Total Count', 'Mean', 'Standard Deviation', 'Minimum', 'Value at 25% Percentile', 'Median (50% Percentile)', 'Value at 75% Percentile', 'Maximum']
    basic_stats.loc[basic_stats.Field.isin(['Mean', 'Standard Deviation']), 'Value'] = basic_stats.loc[basic_stats.Field.isin(['Mean', 'Standard Deviation']), 'Value'].apply(lambda x: np.round(x, 2))
    basic_stats.loc[~basic_stats.Field.isin(['Mean', 'Standard Deviation']), 'Value'] = basic_stats.loc[~basic_stats.Field.isin(['Mean', 'Standard Deviation']), 'Value'].apply(int).apply(str)
    return basic_stats

  ser = data[col].value_counts()
  ser.name = 'Absolute Number'

  percentage_ser = np.round(ser / len(data) * 100, 2)
  percentage_ser.name = 'Proportion in Data (%)'

  cumsum_percentage_ser = percentage_ser.cumsum()
  cumsum_percentage_ser.name = 'Cumulative Proportion (%)'

  full_value_counts_df = pd.concat([ser, percentage_ser, cumsum_percentage_ser], axis=1)

  if plot_top_k > top_k:
    top_k = plot_top_k

  if top_k == -1:
    top_k = sum(cumsum_percentage_ser <= thres) + 1
    top_k = max(5, top_k)
    top_k = min(20, top_k)

  value_counts_df = full_value_counts_df if return_full else full_value_counts_df[:top_k]

  if top_k < len(full_value_counts_df) and not return_full:
    print(f'{len(full_value_counts_df)-top_k} more rows are available, add "return_full = True" if you want to see all.\n')

  plot_top_k = 10 if plot_top_k == -1 else plot_top_k
  graph_df = value_counts_df['Proportion in Data (%)'][:plot_top_k].copy()

  if plot_type == '':
    plot_type = 'bar' if graph_df.sum() < thres else 'pie'

  if plot_type == 'pie':

    fig, ax = plt.subplots(figsize=(9, 6), dpi=default_dpi, subplot_kw=dict(aspect="equal"))

    values = graph_df.values.tolist()
    names = graph_df.index.tolist()

    def func(pct, allvals):
      absolute = int(pct / 100. * np.sum(allvals))
      return "{:.1f}%".format(pct, absolute)

    wedges, texts, autotexts = ax.pie(values, autopct=lambda pct: func(pct, values), textprops=dict(color="w"))

    for w in wedges:
      w.set_edgecolor('white')

    ax.legend(wedges, names,
              title="Categories",
              loc="center left",
              bbox_to_anchor=(1, 0, 0.8, 1))

    plt.setp(autotexts, size=12, weight="bold")

    ax.set_title(f"Relative Proportion of Top {len(graph_df)} {col}" if len(graph_df) < len(full_value_counts_df) else f"Proportion of {col}")

  if plot_type == 'bar':
    plt.figure(figsize=(9, 6), dpi=default_dpi)
    graph_df.plot(kind='bar')
    plt.title(f"Barplot of the Top {len(graph_df)} {col} - (y axis shows percentage)")

  print()

  return value_counts_df


# # -----------------------------Correlation & Regression------------------------------------------

# def show_corr(cols, data=regression_df):

#   if isinstance(cols, str):
#     cols = cols.strip().split()
#   try:
#     corr_df = data[cols].copy().corr()
#   except KeyError as e:
#     print('Variable "' + re.findall(r"\[\'(.*?)\'\]", str(e))[0] + '" not found, check your spelling please.')
#     return

#   cmap = sns.diverging_palette(10, 130, as_cmap=True)  # red green

#   corr = corr_df.values
#   np.fill_diagonal(corr, np.nan)
#   corr = np.triu(corr, k=1)
#   corr[corr == 0] = np.nan
#   labels = corr_df.columns

#   plt.figure(figsize=(5, 4), dpi=default_dpi)
#   sns.heatmap(corr, cmap=cmap, vmin=-1, vmax=1, center=0, annot=True, xticklabels=labels, yticklabels=labels)


# def run_regression(design, data=regression_df):
#   variables = design.replace('~', ' ').replace('+', ' ').split()
#   selected_data = data[variables].copy()
#   scaled_data = pd.DataFrame(sklearn.preprocessing.RobustScaler().fit_transform(X=selected_data), columns=selected_data.columns)
#   y, X = patsy.dmatrices(design, data=scaled_data, return_type='dataframe')   # Split data columns
#   mod = sm.OLS(y, X)
#   res = mod.fit()
#   print(res.summary())
