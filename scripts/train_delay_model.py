import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import joblib

def generate_synthetic_data(n_samples=10000):
    np.random.seed(42)
    
    # Feature distributions based on expected ranges
    otd = np.random.uniform(50, 100, n_samples)
    var_days = np.random.uniform(0, 14, n_samples)
    transit_days = np.random.uniform(1, 45, n_samples)
    lane_rel = np.random.uniform(50, 100, n_samples)
    order_ratio = np.random.uniform(0.1, 5.0, n_samples)
    
    # Underlying true relationships to simulate real-world logistics behavior
    b0 = -4.5
    b_var = 0.35
    b_size = 0.40
    
    z = (
        b0 +
        1.5 * (1.0 - (otd / 100.0)) +
        b_var * var_days +
        0.05 * transit_days +
        2.0 * (1.0 - (lane_rel / 100.0)) +
        b_size * order_ratio
    )
    
    # Calculate probability of delay > 3 days
    p_delay = 1.0 / (1.0 + np.exp(-z))
    
    # Generate noisy boolean labels based on probabilities
    delayed_gt_3 = np.random.binomial(1, p_delay)
    
    df = pd.DataFrame({
        'otd': otd,
        'var_days': var_days,
        'transit_days': transit_days,
        'lane_rel': lane_rel,
        'order_ratio': order_ratio,
        'delayed_gt_3': delayed_gt_3
    })
    
    return df

def train_and_evaluate():
    print("Generating 10,000 synthetic historical PO records...")
    df = generate_synthetic_data()
    
    X = df[['otd', 'var_days', 'transit_days', 'lane_rel', 'order_ratio']]
    y = df['delayed_gt_3']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training Logistic Regression Model...")
    model = LogisticRegression()
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    print("\n--- Evaluation Metrics ---")
    print(f"Accuracy:  {accuracy_score(y_test, y_pred):.4f}")
    print(f"Precision: {precision_score(y_test, y_pred):.4f}")
    print(f"Recall:    {recall_score(y_test, y_pred):.4f}")
    print(f"F1-Score:  {f1_score(y_test, y_pred):.4f}")
    print(f"ROC-AUC:   {roc_auc_score(y_test, y_prob):.4f}")
    
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'engine', 'delay_model.pkl')
    joblib.dump(model, model_path)
    print(f"\nModel saved to {model_path}")

if __name__ == "__main__":
    train_and_evaluate()
