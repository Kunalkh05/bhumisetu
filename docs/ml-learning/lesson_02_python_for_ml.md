# Lesson 2: Python for ML (NumPy, pandas, DataFrames, Vectors)

Welcome to **Lesson 2** of the **BHUMISETU AI/ML Track**.

In Lesson 1, we learned that Machine Learning discovers mathematical relationships between a **Feature Matrix ($X$)** and a **Target Vector ($y$)**.
In this lesson, we will master the actual computational machinery used to represent, manipulate, and compute on that data: **NumPy** and **pandas**.

---

## 1. Why Standard Python is Too Slow for ML

In standard Python, a `list` is a collection of pointers to arbitrary heap-allocated objects:
```python
cases = [142, 210, 58, 305]  # Python stores 4 distinct integer objects in scattered memory!
```
When you iterate over a Python list with a `for` loop:
1. Python must fetch each object pointer.
2. Check its data type dynamically (type-checking overhead).
3. Extract the raw integer value.
4. Execute CPU instruction.

If you have $100,000$ land parcels across Maharashtra, a nested Python loop will crawl at snail's pace.

### The NumPy Revolution: Contiguous Memory & C Speed
NumPy introduces the **`ndarray` (N-Dimensional Array)**:
- Stores numbers of identical data types (e.g., 64-bit float: `float64`) in a single **contiguous block of memory**.
- Operations bypass the Python interpreter and run compiled C/Fortran SIMD (Single Instruction, Multiple Data) instructions directly on the CPU.
- **Speed advantage**: NumPy calculations are typically **$50\times$ to $200\times$ faster** than standard Python loops!

```python
import numpy as np

# Standard Python loop:
# for x in data: x * 2.5 (Slow)

# NumPy vectorized instruction:
arr = np.array([142.0, 210.0, 58.0, 305.0])
scaled_arr = arr * 2.5  # Executed in a single CPU cycle via SIMD!
```

---

## 2. Dimensionality: Scalars, Vectors, Matrices, and Tensors

Every concept in modern Machine Learning is built on dimensions:

| Math Object | NumPy Dimension (`arr.ndim`) | Shape (`arr.shape`) | Real BHUMISETU Example |
| :--- | :---: | :---: | :--- |
| **Scalar** | `0` | `()` | Single regularization penalty `penalizer = 0.05` |
| **Vector** | `1` | `(N,)` or `(D,)` | Target durations $\mathbf{y}$ for $N$ cases: `[180, 240, 95, ...]` |
| **Matrix** | `2` | `(N, D)` | Feature Matrix $X$: $N$ land cases $\times D$ features |
| **Tensor** | $\ge 3$ | `(B, T, D)` | Multi-temporal snapshots across case timelines |

### Understanding Matrix Shape: $(N, D)$
In tabular ML, you will see $N \times D$ everywhere:
- **$N$** = Number of rows (samples/observations, e.g., $1,250$ land cases).
- **$D$** = Number of columns (features/predictors, e.g., $18$ indicators).

```python
# A matrix of 3 land acquisition cases with 2 features each:
# Feature 0: days in inquiry
# Feature 1: objection count
X = np.array([
    [120.0, 3.0],   # Case 1
    [245.0, 8.0],   # Case 2
    [45.0,  0.0]    # Case 3
])

print(X.shape)  # Output: (3, 2) -> 3 cases, 2 features
print(X.ndim)   # Output: 2 -> 2-dimensional matrix
```

---

## 3. Vectorization & Matrix Multiplication ($X\mathbf{w}$)

Recall our linear formula from Lesson 1: $\hat{y} = w \cdot x + b$.

When we have multiple features ($x_1, x_2, \dots, x_D$), we have a vector of weights $\mathbf{w} = [w_1, w_2, \dots, w_D]^T$.
To calculate the prediction for all $N$ cases simultaneously, we use **Matrix Multiplication**:

$$\mathbf{\hat{y}} = X \mathbf{w} + b$$

### Example in NumPy:
```python
import numpy as np

# Feature Matrix X: 3 cases, 2 features (days, objections)
X = np.array([
    [100.0, 2.0],
    [200.0, 5.0],
    [50.0,  0.0]
])

# Weight vector w: weight for days = 0.5, weight for objections = 15.0
w = np.array([0.5, 15.0])

# Intercept b (base timeline)
b = 30.0

# Vectorized prediction using the matrix multiplication operator `@`:
# No for-loops! Computes all 3 predictions in parallel.
y_hat = X @ w + b

# Breakdown of math:
# Case 1: (100 * 0.5) + (2 * 15.0) + 30 = 50 + 30 + 30 = 110
# Case 2: (200 * 0.5) + (5 * 15.0) + 30 = 100 + 75 + 30 = 205
# Case 3: (50 * 0.5)  + (0 * 15.0) + 30 = 25 + 0 + 30  = 55
print(y_hat)  # Output: [110. 205.  55.]
```

---

## 4. pandas: The Standard for Tabular Data

While NumPy handles raw numerical arrays, **pandas** provides labels, column names, missing data handling, and relational operations.

### Key Data Structures:
1. **`pd.Series`**: A 1D labeled array (like a single column with an index).
2. **`pd.DataFrame`**: A 2D labeled table composed of multiple Series sharing the same index.

```python
import pandas as pd

data = {
    "case_id": ["MH-PUN-01", "MH-SOL-02", "MH-NSK-03"],
    "district": ["Pune", "Solapur", "Nashik"],
    "days_in_stage": [120, 310, 45],
    "objection_count": [4, 12, 1],
    "event_observed": [1, 0, 1]
}

df = pd.DataFrame(data)
print(df)
```

Output:
```
     case_id district  days_in_stage  objection_count  event_observed
0  MH-PUN-01     Pune            120                4               1
1  MH-SOL-02  Solapur            310               12               0
2  MH-NSK-03   Nashik             45                1               1
```

### Accessing Data: `.loc` vs `.iloc`
A critical source of bugs in data science is confusing label-based and index-based slicing:
- **`df.iloc[row_idx, col_idx]`**: Pure integer position (like standard Python array indexing).
  ```python
  df.iloc[0, 2]       # Row 0, Column 2 -> 120
  df.iloc[0:2, 1:4]   # First 2 rows, columns 1 to 3
  ```
- **`df.loc[row_label, col_name]`**: Label-based indexing (uses row index and column strings).
  ```python
  df.loc[0, "district"]   # 'Pune'
  df.loc[:, ["district", "days_in_stage"]]  # All rows for specific columns
  ```

---

## 5. Essential ML Data Operations with pandas

In real production systems like BHUMISETU, we perform 5 recurring operations before training any model:

### 1. Boolean Masking & Cohort Filtering
We only want to train on a specific statutory stage (e.g., Section 11 to Section 19):
```python
# Create a boolean mask
mask = df["days_in_stage"] > 100

# Filter DataFrame
delayed_cases = df[mask].copy()
```

### 2. Missing Data Identification & Imputation
In government land records, some fields might not be reported yet (`NaN` = Not a Number).
```python
# Check how many missing values exist in each column:
print(df.isna().sum())

# Median imputation (replacing missing values with the median of known cases):
median_objections = df["objection_count"].median()
df["objection_count"] = df["objection_count"].fillna(median_objections)
```

### 3. Detecting Zero Variance (Useless Features)
If every single case has `act_key = "RFCTLARR_2013"`, that column contains **zero variance** (`nunique() == 1`). A machine learning model cannot learn anything from a constant column:
```python
if df["act_key"].nunique() <= 1:
    df = df.drop(columns=["act_key"])  # Safe pruning
```

### 4. Detecting Collinearity (Redundant Features)
If two features move together in lockstep (Pearson correlation $r > 0.98$), including both destabilizes statistical models:
```python
correlation = df["days_since_initiation"].corr(df["days_in_stage"])
if abs(correlation) > 0.98:
    df = df.drop(columns=["days_since_initiation"])
```

### 5. One-Hot Encoding Categoricals (`pd.get_dummies`)
Mathematical models cannot multiply the string `"Pune"` by a weight $w$. We convert categorical text columns into binary $(0/1)$ indicator columns:
```python
# Convert district into binary columns: district_Pune, district_Solapur, etc.
# drop_first=True avoids the "dummy variable trap" (multicollinearity)
df_encoded = pd.get_dummies(df, columns=["district"], drop_first=True)
```

---

## 6. Real BHUMISETU Source Code Inspection

Let's examine how this exact logic is written in our production repository: [`bhumi-setu/ml/src/training/cox_baseline.py`](file:///Users/sakshantwaghmare/Projects/bhumisetu/bhumi-setu/ml/src/training/cox_baseline.py#L71-L180).

Here is the annotated production function `prepare_cox_design_matrix`:

```python
# 1. Load CSVs into pandas DataFrames
feats = pd.read_csv(f_path)
targs = pd.read_csv(t_path)

# 2. Relational join on identifier keys (case_id, snapshot_id, transition)
df = pd.merge(feats, targs, on=list(IDENTIFIER_COLUMNS))

# 3. Filter for specific transition cohort using boolean mask
sub = df[df["transition"] == transition].copy()

# 4. Check for structural missingness (> 50% missing -> exclude)
missing_count = sub[col].isna().sum()
if missing_count > 0.5 * len(sub):
    candidate_cols.remove(col)

# 5. Check for zero variance
if sub[col].nunique() <= 1:
    candidate_cols.remove(col)

# 6. Check for high collinearity
corr = sub["derived_days_in_current_stage"].corr(sub[redundant])
if abs(corr) > 0.98:
    candidate_cols.remove(redundant)

# 7. Impute remaining missing values with column median
if X_df[col].isna().any():
    median_val = X_df[col].median()
    X_df[col] = X_df[col].fillna(median_val)

# 8. One-hot encode categoricals
X_enc = pd.get_dummies(X_df, drop_first=True)

# 9. Extract target duration as a NumPy vector
X_enc["duration"] = sub["duration_at_risk_days"].values
```

Notice how clean and deterministic this pipeline is! Everything we just learned maps directly to production code.

---

## 7. Mini Quiz (5 Questions)

Answer these in your mind or reply in chat:

1. Why does an ML algorithm crash or produce corrupted weights if you feed in a column with string values like `"Solapur"` or `"Pune"` without encoding it first?
2. What is the difference between `df.iloc[0:5, 1]` and `df.loc[0:5, "objection_count"]`?
3. If an array has `shape = (150, 6)`, how many cases (observations) and how many features does it have?
4. In `pd.get_dummies(df, columns=["district"], drop_first=True)`, why do we set `drop_first=True`?
5. Why is matrix multiplication `X @ w` exponentially faster than using a Python `for` loop across thousands of rows?

---

## 8. Hands-on Coding Challenge

Here is a self-contained Python script modeling a simplified BHUMISETU risk calculation.
Run this script or solve it step-by-step:

```python
import numpy as np
import pandas as pd

# Historical Land Acquisition Cases
raw_data = {
    "case_id": ["CASE_101", "CASE_102", "CASE_103", "CASE_104"],
    "district": ["Pune", "Thane", "Pune", "Thane"],
    "days_in_stage": [150.0, 320.0, 80.0, np.nan],  # Notice CASE_104 has missing days!
    "objection_count": [2, 7, 0, 4],
}

df = pd.DataFrame(raw_data)

# Step A: Impute missing days_in_stage with the column median
# YOUR CODE HERE

# Step B: One-hot encode "district" with drop_first=True
# Convert boolean results to int (1/0)
# YOUR CODE HERE

# Step C: Select only numeric predictor columns into matrix X
# (days_in_stage, objection_count, district_Thane)
# Convert X to a NumPy float array: X = X_df.values

# Step D: Given learned weight vector w and intercept b:
# weights: [0.1 (days), 5.0 (objections), 12.0 (district_Thane)]
# intercept: 20.0
# Compute predicted delay score vector using vector multiplication: y_hat = X @ w + b
```

---

Take your time to inspect the code and quiz. When you're ready, share your answers or questions!
