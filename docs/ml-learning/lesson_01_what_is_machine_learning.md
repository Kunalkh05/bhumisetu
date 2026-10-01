# Lesson 1: What is Machine Learning? (Rules vs Data, Features, Targets, Parameters)

---

## 1. High-Level Intuition

In traditional software engineering, developers write deterministic rules:
```
[ Input Data ] + [ Human-Written Code (Rules) ] ──▶ [ Output / Decisions ]
```
Example:
```python
if days_in_current_stage > 365:
    alert = "Case is delayed"
```
The computer blindly follows explicit rules. If edge cases exist (e.g., highway acquisitions in Pune vs. irrigation canal acquisitions in Solapur), the human programmer must handcraft every condition.

**Machine Learning (ML)** inverts this process:
```
[ Historical Input Data (X) ] + [ Known Historical Outcomes (y) ] ──▶ [ Learning Algorithm ]
                                                                             │
                                                                             ▼
                                                                     [ Learned Model ]
```
Once the relationship is learned, new unseen cases can be evaluated:
```
[ New Case Data ] + [ Learned Model ] ──▶ [ Predicted Outcome (ŷ) ]
```

---

## 2. Core Terminology Grounded in BHUMISETU

| ML Term | Plain English Meaning | BHUMISETU Example |
| :--- | :--- | :--- |
| **Observation / Sample** | A single historical record / row | One landmark snapshot of case `MH-PUN-2024-0012` |
| **Feature ($x$)** | Known attribute at the time of prediction | `derived_days_in_current_stage = 142`, `district = "Pune"` |
| **Feature Matrix ($X$)** | Tabular collection of features for all cases | $N \times D$ table of safe historical covariates |
| **Target ($y$)** | The outcome we want to predict | `duration_at_risk_days = 210` until Section 19 declaration |
| **Parameters ($w, b$)** | Internal weights learned from historical data | Risk multiplier $\beta$ for high-objection cases |
| **Hyperparameters** | Configuration knobs set *before* training | `penalizer = 0.05` for Cox regression |
| **Training** | The process where the algorithm learns parameters | Fitting model weights on 2018–2023 historical records |
| **Inference / Serving** | Using learned parameters to score new live data | Officer Dashboard showing 84% delay probability in <2ms |

---

## 3. Mathematical Formulation of a Linear Predictor

$$\hat{y} = w \cdot x + b$$

- $x$: Input feature (e.g., elapsed days in inquiry).
- $w$: Parameter / weight (slope), determining how sensitive the prediction is to changes in $x$.
- $b$: Bias / intercept, determining the baseline prediction when $x = 0$.
- $\hat{y}$: Model estimate ("y-hat").

---

## 4. Lesson 1 Quiz Solutions

### Question 1: Feature vs Target in BHUMISETU
- **Feature ($x$)**: An input variable observed *at or before* the decision snapshot date. Example: `derived_days_in_current_stage`, `objection_count`, or `district`.
- **Target ($y$)**: The future ground truth outcome the model aims to estimate. Example: `duration_at_risk_days` (how many days until Section 19 is declared) or `event_observed` (whether the transition completed or was censored).

### Question 2: Training vs Inference
- **Training**: Computationally intensive offline optimization where the algorithm scans historical $(X, y)$ pairs to calculate optimal parameters ($w, b$ or $\beta$). Done periodically (e.g., monthly).
- **Inference**: High-speed runtime evaluation where new feature vector $x_{\text{new}}$ is multiplied by pre-calculated parameters to produce $\hat{y}$. This is what executes in $\approx 1.3\text{ ms}$ when an officer views a dashboard.

### Question 3: Parameters vs Hyperparameters
- `penalizer = 0.05` is a **Hyperparameter**. It is a configuration knob set manually by the ML engineer *before* training to control regularization, not something calculated automatically from the data.

### Question 4: $\hat{y} = w \cdot x + b$ Components
- $x$: Input feature.
- $w$: Weight / slope parameter learned from data.
- $b$: Bias / intercept term.
- $\hat{y}$: Model prediction ("y-hat").

### Question 5: Why `award_recorded = True` is Catastrophic
- Including `award_recorded` creates **target data leakage**. An award only occurs *at the end* of the land acquisition lifecycle. At the moment an officer is predicting risk during Section 11 inquiry, the award hasn't happened. If included, the model will cheat, assign all weight to this column, and fail completely in live production.

---

## 5. Coding Exercise Solution

Given:
- Case 1: $x = 10, y = 190$
- Case 2: $x = 20, y = 180$
- Case 3: $x = 30, y = 170$

Formula: $y = w \cdot x + b$

1. **Calculate $w$ (slope)**:
   $$w = \frac{180 - 190}{20 - 10} = \frac{-10}{10} = -1.0$$
2. **Calculate $b$ (intercept)**:
   $$190 = (-1.0 \cdot 10) + b \implies b = 200$$
3. **Inference on `new_case` ($x = 50$)**:
   $$\hat{y} = (-1.0 \cdot 50) + 200 = 150 \text{ days remaining}$$
