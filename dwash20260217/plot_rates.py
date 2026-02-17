import re
import matplotlib.pyplot as plt

import re
import matplotlib.pyplot as plt
import numpy as np

files = ['run1.txt', 'run2.txt']
# We'll collect data per model per run
model_names = []
run1_pass1 = []
run1_pass2 = []
run2_pass1 = []
run2_pass2 = []

# Regex to parse the block format
# Captures: Model Name (group 1), Pass Rate 1 (group 2), Pass Rate 2 (group 3)
pattern = re.compile(r'===\s+.*?openrouter-(.*?)\s+===\n\s+pass_rate_1:\s+([\d.]+)\n\s+pass_rate_2:\s+([\d.]+)')

# First pass: collect all unique model names in order they appear in run1
# (assuming run1 has all models)
with open('run1.txt', 'r') as f:
    content = f.read()
    matches = pattern.findall(content)
    for m in matches:
        name = m[0].replace('primary-variation-', '')
        model_names.append(name)
        run1_pass1.append(float(m[1]))
        run1_pass2.append(float(m[2]))

# Second pass: fill run2 data in same order, default to 0 if missing
run2_data = {}
with open('run2.txt', 'r') as f:
    content = f.read()
    matches = pattern.findall(content)
    for m in matches:
        name = m[0].replace('primary-variation-', '')
        run2_data[name] = (float(m[1]), float(m[2]))

for name in model_names:
    if name in run2_data:
        p1, p2 = run2_data[name]
        run2_pass1.append(p1)
        run2_pass2.append(p2)
    else:
        run2_pass1.append(0.0)
        run2_pass2.append(0.0)

# Plotting
fig, ax = plt.subplots(figsize=(14, len(model_names) * 0.8))

# Y positions for the bars
y_pos = np.arange(len(model_names))
height = 0.35

# For each model we want two groups: run1 and run2 side by side
# Each group will have a stacked bar showing pass1 (bottom) and pass2 (top)
# We'll plot run1 bars at y - height/2 and run2 bars at y + height/2

# Plot run1 stacked bars
ax.barh(y_pos - height/2, run1_pass1, height, label='Run 1 Pass 1', color='#a0cbe8', edgecolor='black')
ax.barh(y_pos - height/2, [run1_pass2[i] - run1_pass1[i] for i in range(len(model_names))], height,
        left=run1_pass1, label='Run 1 Pass 2', color='#4e79a7', edgecolor='black')

# Plot run2 stacked bars
ax.barh(y_pos + height/2, run2_pass1, height, label='Run 2 Pass 1', color='#ffb366', edgecolor='black')
ax.barh(y_pos + height/2, [run2_pass2[i] - run2_pass1[i] for i in range(len(model_names))], height,
        left=run2_pass1, label='Run 2 Pass 2', color='#ff8000', edgecolor='black')

ax.set_yticks(y_pos)
ax.set_yticklabels(model_names)
ax.set_xlabel('Pass Rate (%)')
ax.set_title('Model Pass Rates: Run 1 vs Run 2 (Pass 1 bottom, Pass 2 top)')
ax.legend()
ax.grid(axis='x', linestyle='--', alpha=0.7)

# Adjust layout to fit long model names
plt.tight_layout()
plt.savefig('benchmark_graph.png')
print("Graph saved to benchmark_graph.png")
