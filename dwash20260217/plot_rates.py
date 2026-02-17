import re
import matplotlib.pyplot as plt

from collections import defaultdict
import numpy as np

files = ['run1.txt', 'run2.txt']
# Dictionary to store lists of results for each model
model_data = defaultdict(lambda: {'pass_1': [], 'pass_2': []})

# Regex to parse the block format
# Captures: Model Name (group 1), Pass Rate 1 (group 2), Pass Rate 2 (group 3)
pattern = re.compile(r'===\s+.*?openrouter-(.*?)\s+===\n\s+pass_rate_1:\s+([\d.]+)\n\s+pass_rate_2:\s+([\d.]+)')

for filename in files:
    try:
        with open(filename, 'r') as f:
            content = f.read()
            matches = pattern.findall(content)
            for m in matches:
                # Clean up model name slightly if needed
                name = m[0].replace('primary-variation-', '')
                model_data[name]['pass_1'].append(float(m[1]))
                model_data[name]['pass_2'].append(float(m[2]))
    except FileNotFoundError:
        print(f"Error: {filename} not found.")

# Calculate averages for plotting
models = sorted(model_data.keys())
avg_pass_1 = [np.mean(model_data[m]['pass_1']) for m in models]
avg_pass_2 = [np.mean(model_data[m]['pass_2']) for m in models]

# Plotting
fig, ax = plt.subplots(figsize=(12, len(models) * 0.8))

# Y positions for the bars
y_pos = np.arange(len(models))
height = 0.35

# Plot horizontal bars side-by-side
# We shift the bars so they don't overlap
ax.barh(y_pos - height/2, avg_pass_1, height, label='Pass Rate 1 (Avg)', color='#a0cbe8')
ax.barh(y_pos + height/2, avg_pass_2, height, label='Pass Rate 2 (Avg)', color='#4e79a7')

ax.set_yticks(y_pos)
ax.set_yticklabels(models)
ax.set_xlabel('Pass Rate (%)')
ax.set_title('Model Pass Rates (Run 1 & Run 2)')
ax.legend()
ax.grid(axis='x', linestyle='--', alpha=0.7)

# Adjust layout to fit long model names
plt.tight_layout()
plt.savefig('benchmark_graph.png')
print("Graph saved to benchmark_graph.png")
