import re
import matplotlib.pyplot as plt
import numpy as np

# Read data from both files
model_names = []
run1_pass1 = []
run1_pass2 = []
run2_pass1 = []
run2_pass2 = []

# Regex to parse the block format
pattern = re.compile(
    r"===\s+.*?openrouter-(.*?)\s+===\n\s+pass_rate_1:\s+([\d.]+)\n\s+pass_rate_2:\s+([\d.]+)"
)

# Read run1.txt
with open("run1.txt", "r") as f:
    content = f.read()
    matches = pattern.findall(content)
    for m in matches:
        name = m[0].replace("primary-variation-", "")
        model_names.append(name)
        run1_pass1.append(float(m[1]))
        run1_pass2.append(float(m[2]))

# Read run2.txt and match to same model order
run2_data = {}
with open("run2.txt", "r") as f:
    content = f.read()
    matches = pattern.findall(content)
    for m in matches:
        name = m[0].replace("primary-variation-", "")
        run2_data[name] = (float(m[1]), float(m[2]))

# Fill run2 data in the same order as model_names
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

# Y positions for each model
y_pos = np.arange(len(model_names))
# We'll have 2 bars per model (run1 and run2), each showing pass1 to pass2 range
bar_width = 0.35
# Positions for run1 and run2 bars
y_run1 = y_pos - bar_width/2
y_run2 = y_pos + bar_width/2

# For each bar, we want to show pass1 as the start and pass2 as the end
# We'll use barh with left=pass1 and width=(pass2 - pass1)
# Run1 bars
ax.barh(
    y_run1,
    [run1_pass2[i] - run1_pass1[i] for i in range(len(model_names))],
    bar_width,
    left=run1_pass1,
    label="Run 1 (Pass 1 → Pass 2)",
    color="#a0cbe8",
    edgecolor="black",
)
# Run2 bars
ax.barh(
    y_run2,
    [run2_pass2[i] - run2_pass1[i] for i in range(len(model_names))],
    bar_width,
    left=run2_pass1,
    label="Run 2 (Pass 1 → Pass 2)",
    color="#ffb366",
    edgecolor="black",
)

# Set y-ticks to model names at the center of each group
ax.set_yticks(y_pos)
ax.set_yticklabels(model_names)
ax.set_xlabel("Pass Rate (%)")
ax.set_title("Model Pass Rates: Range Bars (Pass 1 start, Pass 2 end)")
ax.legend()
ax.grid(axis="x", linestyle="--", alpha=0.7)

# Add vertical lines to separate model groups
for y in y_pos:
    ax.axhline(y + 0.5, color="gray", linestyle="-", linewidth=0.5, alpha=0.3)

plt.tight_layout()
plt.savefig("benchmark_graph.png")
print("Graph saved to benchmark_graph.png")
