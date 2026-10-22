##################################################################################
# This code is to clean and concatonate the ENROLLMENT data from the SHARE Study #
#                         Authored by SHL                                        #
#                    Last edited on: 10/21/2026                                  #
##################################################################################\
    
# load in libraries
import os
import pandas as pd
import csv

# Set directory with all PT files downloaded from OneDrive, CHANGE TO YOUR OWN FILE PATH
in_dir = '/Users/sophialipetzky/Documents/SHARE_ema_analysis/raw_data/v1/'

df_raw = pd.DataFrame()
df_cat = pd.DataFrame()
for root, dirs, files in os.walk(in_dir):
    for file in files: 
        if file.endswith('V1.csv'):
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="latin-1", newline="") as f:
                rows = list(csv.reader(f))         
            records = []
            current_header = None
            problems = []        
            for line_num, row in enumerate(rows, start=1):         
                # Skip rows containing only empty fields
                if not row or all(value.strip() == "" for value in row):
                    continue           
                # Each instrument section starts with its own header
                if row[0].strip() == "Instrument Name":
                    current_header = row
                    continue         
                if current_header is None:
                    continue            
                # Preserve any unexpected extra fields instead of dropping them
                header = current_header.copy()            
                if len(row) != len(header):
                    problems.append(
                        (line_num, row[0], len(row), len(header))
                    )           
                    if len(row) > len(header):
                        header += [
                            f"extra_field_{i}"
                            for i in range(1, len(row) - len(header) + 1)
                        ]
                    else:
                        row = row + [""] * (len(header) - len(row))
            
                records.append(dict(zip(header, row)))
            
            df_raw = pd.DataFrame(records)
            df_cat = pd.concat([df_cat, df_raw])

print("Data shape:", df_cat.shape)
print(df_cat["Instrument Name"].value_counts(dropna=False))
print("Rows with field-count mismatches:", problems)

id_cols = ["URSI", "Instrument Name", "Assessment ID"]

value_cols = [
    col for col in df_cat.columns
    if col not in id_cols
    and col not in [
        "Subject Type", "Rater1", "Assessment Date",
        "Visit", "Visit Instance", "Entry Code",
        "Entry Start", "Entry End", "Entry Username"
    ]
]
# Pivot questionnaire variables into participant-level columns
df_wide = df_cat.pivot_table(
    index="URSI",
    columns="Instrument Name",
    values=value_cols,
    aggfunc="first"
)
# Flatten the multi-level column names
df_wide.columns = [
    f"{instrument}_{variable}"
    for variable, instrument in df_wide.columns
]
df_wide = df_wide.reset_index()

# Change to numeric values
numeric_cols = df_wide.columns[1:419].difference(['V1 Demographics_enroll_race-1'])
df_wide = df_wide.copy()
df_numeric = df_wide[numeric_cols].apply(pd.to_numeric, errors='coerce')
df_wide = pd.concat(
    [
        df_wide.iloc[:, :1],
        df_numeric,
        df_wide.iloc[:, 419:],
        df_wide[['V1 Demographics_enroll_race-1']]
    ],
    axis=1
)

# Reverse code CTQ questions (#2, 5, 7, 13, 19, 26, 28)
ctq_reverse = [f"CTQ_ctq_q{i}-1" for i in [2, 5, 7, 12, 19, 26, 28]]
df_wide[ctq_reverse] = 6 - df_wide[ctq_reverse]

# Set variables to sum
ctq_total = [f"CTQ_ctq_q{i}-1" for i in range(1, 29)]
dmqr_con_total = [f"DMQ-R_dmqr_{i}-1" for i in [2, 8, 12, 19, 20]]
dmqr_cop_total = [f"DMQ-R_dmqr_{i}-1" for i in [1, 4, 6, 15, 17]]
dmqr_enh_total = [f"DMQ-R_dmqr_{i}-1" for i in [7, 9, 10, 13, 18]]
dmqr_soc_total = [f"DMQ-R_dmqr_{i}-1" for i in [3, 5, 11, 14, 16]]
pcl_total = [f"PCL-5_pcl5_{i}-1" for i in range(1, 21)]
audit_total = [f"AUDIT_ver2_audit_q{i}-1" for i in range(1, 11)]



# Add total scores for measures if they are missing
for i in range(len(df_wide)):
    if pd.isna(df_wide.loc[i, 'CTQ_ctq_total_score-1']):
        df_wide.loc[i, 'CTQ_ctq_total_score-1'] = df_wide.loc[i, ctq_total].sum()
    if pd.isna(df_wide.loc[i, 'DMQ-R_dmqr_con_score-1']):
        df_wide.loc[i, 'DMQ-R_dmqr_con_score-1'] = df_wide.loc[i, dmqr_con_total].sum()
        df_wide.loc[i, 'DMQ-R_dmqr_cop_score-1'] = df_wide.loc[i, dmqr_cop_total].sum()
        df_wide.loc[i, 'DMQ-R_dmqr_enh_score-1'] = df_wide.loc[i, dmqr_enh_total].sum()
        df_wide.loc[i, 'DMQ-R_dmqr_soc_score-1'] = df_wide.loc[i, dmqr_soc_total].sum()
    if pd.isna(df_wide.loc[i, 'PCL-5_pcl5_total-1']):
        df_wide.loc[i, 'PCL-5_pcl5_total-1'] = df_wide.loc[i, pcl_total].sum()
    if pd.isna(df_wide.loc[i, 'AUDIT_ver2_audit_score-1']):
        df_wide.loc[i, 'AUDIT_ver2_audit_score-1'] = df_wide.loc[i, audit_total].sum()

# get all column names
column_names = df_wide.columns.tolist()

# Set demographic variables (can change to any demographic variables of interest by looking through column_names!!)
demo = ["URSI", "V1 Demographics_bio_sex-1", "V1 Demographics_enroll_race-1", "V1 Demographics_enroll_hispanic-1", "V1 Demographics_enroll_income-1"]

# Set total scores for measures of interest
totals = ["CTQ_ctq_total_score-1", "DMQ-R_dmqr_con_score-1", "DMQ-R_dmqr_cop_score-1", "DMQ-R_dmqr_enh_score-1", "DMQ-R_dmqr_soc_score-1",
          "PCL-5_pcl5_total-1", "AUDIT_ver2_audit_score-1"]

# Create final dataframe with variables of interest
df_clean = df_wide[demo + totals]

# Download final .csv file with your desired variables, CHANGE TO YOUR OWN FILE PATH
df_clean.to_csv(in_dir+'../clean_data/clean_v1.csv', index = False)


