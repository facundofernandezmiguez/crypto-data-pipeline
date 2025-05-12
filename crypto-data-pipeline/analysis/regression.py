"""
Regression model training and evaluation for cryptocurrency price prediction.

This module handles:
1. Loading preprocessed data from feature_engineering.py
2. Training regression models
3. Evaluating model performance
4. Saving trained models
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib

def load_data(csv_path='data/processed_features.csv'):
    """Load preprocessed feature data."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Data file not found: {csv_path}. Run feature_engineering.py first.")
    
    return pd.read_csv(csv_path)

def train_models(X_train, y_train):
    """Train various regression models."""
    models = {
        'Linear Regression': LinearRegression(),
        'Ridge Regression': Ridge(alpha=1.0),
        'Lasso Regression': Lasso(alpha=0.1),
        'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42)
    }
    
    trained_models = {}
    for name, model in models.items():
        print(f"Training {name}...")
        model.fit(X_train, y_train)
        trained_models[name] = model
    
    return trained_models

def evaluate_models(models, X_test, y_test):
    """Evaluate model performance on test data."""
    results = {}
    
    for name, model in models.items():
        y_pred = model.predict(X_test)
        
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        results[name] = {
            'MSE': mse,
            'RMSE': rmse,
            'MAE': mae,
            'R²': r2
        }
        
        print(f"\nResults for {name}:")
        print(f"MSE: {mse:.4f}")
        print(f"RMSE: {rmse:.4f}")
        print(f"MAE: {mae:.4f}")
        print(f"R²: {r2:.4f}")
    
    return results

def plot_predictions(model, X_test, y_test, model_name, output_dir='data'):
    """Plot actual vs predicted values."""
    y_pred = model.predict(X_test)
    
    plt.figure(figsize=(10, 6))
    plt.scatter(y_test, y_pred, alpha=0.5)
    
    # Plot the perfect prediction line
    min_val = min(min(y_test), min(y_pred))
    max_val = max(max(y_test), max(y_pred))
    plt.plot([min_val, max_val], [min_val, max_val], 'r--')
    
    plt.xlabel('Actual Values')
    plt.ylabel('Predicted Values')
    plt.title(f'{model_name}: Actual vs Predicted')
    
    # Save the plot
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f'{output_dir}/{model_name.replace(" ", "_").lower()}_predictions.png')
    plt.close()

def save_models(models, output_dir='data/models'):
    """Save trained models to disk."""
    os.makedirs(output_dir, exist_ok=True)
    
    for name, model in models.items():
        filename = f'{output_dir}/{name.replace(" ", "_").lower()}.joblib'
        joblib.dump(model, filename)
        print(f"Model saved: {filename}")

def main():
    """Main function to run the regression pipeline."""
    # Load preprocessed data
    print("Loading preprocessed data...")
    df = load_data()
    
    # Prepare features and target
    print("Preparing data for modeling...")
    # Assuming the target is 'price_next_day' or similar
    # Adjust feature selection as needed based on feature_engineering.py output
    target_col = 'price_next_day'
    if target_col not in df.columns:
        target_col = 'price'  # Fallback
    
    feature_cols = [col for col in df.columns if col != target_col and col != 'date']
    
    X = df[feature_cols]
    y = df[target_col]
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Train models
    trained_models = train_models(X_train, y_train)
    
    # Evaluate models
    results = evaluate_models(trained_models, X_test, y_test)
    
    # Plot predictions
    for name, model in trained_models.items():
        plot_predictions(model, X_test, y_test, name)
    
    # Save models
    save_models(trained_models)
    
    # Find best model
    best_model = max(results.items(), key=lambda x: x[1]['R²'])
    print(f"\nBest model: {best_model[0]} with R² of {best_model[1]['R²']:.4f}")
    
    return trained_models, results

if __name__ == "__main__":
    main()
