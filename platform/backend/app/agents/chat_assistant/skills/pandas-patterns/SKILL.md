---
name: pandas-patterns
description: Common pandas and matplotlib patterns for data analysis and visualization
---

## Data Loading

### CSV Files
```python
import pandas as pd

# Load CSV file
df = pd.read_csv("data.csv")

# Always check the data first
print(df.info())
print(df.describe())
print(df.head())
```

### JSON Files
```python
import pandas as pd

# Load JSON file
df = pd.read_json("data.json")

# For nested JSON, use json_normalize
from pandas import json_normalize
df = json_normalize(data)
```

## Data Inspection

### Basic Information
```python
# Data types and non-null counts
df.info()

# Statistical summary
df.describe()

# First few rows
df.head()
df.tail()

# Column names
df.columns.tolist()

# Shape
df.shape
```

### Missing Values
```python
# Check for missing values
df.isnull().sum()

# Drop missing values
df.dropna()

# Fill missing values
df.fillna(0)
df.fillna(df.mean())
```

## Data Cleaning

### Rename Columns
```python
df.rename(columns={"old_name": "new_name"}, inplace=True)
```

### Drop Columns
```python
df.drop(columns=["column1", "column2"], inplace=True)
```

### Filter Rows
```python
# Single condition
df[df["column"] > 10]

# Multiple conditions
df[(df["col1"] > 10) & (df["col2"] == "value")]

# String contains
df[df["text_column"].str.contains("keyword")]
```

### Group By
```python
# Group and aggregate
df.groupby("category")["value"].sum()
df.groupby("category")["value"].mean()
df.groupby(["cat1", "cat2"])["value"].count()
```

### Sort
```python
# Sort by column
df.sort_values("column", ascending=False)

# Sort by multiple columns
df.sort_values(["col1", "col2"], ascending=[True, False])
```

## Visualization

### Bar Chart
```python
import matplotlib.pyplot as plt

df.plot(kind="bar", x="category", y="value")
plt.title("Bar Chart Title")
plt.xlabel("Category")
plt.ylabel("Value")
plt.tight_layout()
plt.savefig("bar_chart.png", dpi=150, bbox_inches="tight")
plt.close()
```

### Line Chart
```python
plt.figure(figsize=(10, 6))
plt.plot(df["date"], df["value"])
plt.title("Line Chart Title")
plt.xlabel("Date")
plt.ylabel("Value")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("line_chart.png", dpi=150, bbox_inches="tight")
plt.close()
```

### Scatter Plot
```python
plt.figure(figsize=(10, 6))
plt.scatter(df["x_column"], df["y_column"])
plt.title("Scatter Plot Title")
plt.xlabel("X Label")
plt.ylabel("Y Label")
plt.tight_layout()
plt.savefig("scatter_plot.png", dpi=150, bbox_inches="tight")
plt.close()
```

### Histogram
```python
plt.figure(figsize=(10, 6))
plt.hist(df["value_column"], bins=30)
plt.title("Histogram Title")
plt.xlabel("Value")
plt.ylabel("Frequency")
plt.tight_layout()
plt.savefig("histogram.png", dpi=150, bbox_inches="tight")
plt.close()
```

### Seaborn Statistical Plots
```python
import seaborn as sns

# Box plot
plt.figure(figsize=(10, 6))
sns.boxplot(data=df, x="category", y="value")
plt.title("Box Plot")
plt.tight_layout()
plt.savefig("boxplot.png", dpi=150, bbox_inches="tight")
plt.close()

# Heatmap for correlations
plt.figure(figsize=(10, 8))
sns.heatmap(df.corr(), annot=True, cmap="coolwarm")
plt.title("Correlation Heatmap")
plt.tight_layout()
plt.savefig("heatmap.png", dpi=150, bbox_inches="tight")
plt.close()
```

### Pie Chart
```python
plt.figure(figsize=(8, 8))
df.groupby("category")["value"].sum().plot(kind="pie", autopct="%1.1f%%")
plt.title("Pie Chart")
plt.ylabel("")
plt.tight_layout()
plt.savefig("pie_chart.png", dpi=150, bbox_inches="tight")
plt.close()
```

## Data Export

### Export to CSV
```python
df.to_csv("output.csv", index=False)
```

### Export to JSON
```python
df.to_json("output.json", orient="records")
```

### Export Summary Statistics
```python
summary = {
    "total_rows": len(df),
    "columns": df.columns.tolist(),
    "dtypes": df.dtypes.astype(str).to_dict(),
    "summary_stats": df.describe().to_dict()
}

import json
with open("summary.json", "w") as f:
    json.dump(summary, f, indent=2)
```

## Reporting

### Write Analysis Report
```python
report = f"""# Data Analysis Report

## Overview
- Total Rows: {len(df)}
- Total Columns: {len(df.columns)}

## Key Findings
{df.describe().to_markdown()}

## Insights
[Add your insights here]
"""

with open("report.md", "w") as f:
    f.write(report)
```

## Best Practices

1. **Always save figures** with `plt.savefig()` before `plt.close()` to avoid memory issues
2. **Use `bbox_inches="tight"`** to prevent cutoff labels
3. **Set `dpi=150`** for high-quality images
4. **Always check `df.info()` first** to understand data types
5. **Handle missing values** before analysis
6. **Use `inplace=True`** for operations that modify the dataframe
7. **Close plots** after saving to free memory
8. **Use `tight_layout()`** to prevent label overlap
