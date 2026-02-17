import re
import matplotlib.pyplot as plt

files = ['run1.txt', 'run2.txt']
models = []
pass_rates_1 = []
pass_rates_2 = []

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
                models.append(name)
                pass_rates_1.append(float(m[1]))
                pass_rates_2.append(float(m[2]))
    except FileNotFoundError:
        print(f"Error: {filename} not found.")

# Plotting
fig, ax = plt.subplots(figsize=(12, 8))

# Y positions for the bars
y_pos = range(len(models))
height = 0.35

# Plot horizontal bars
# We put Models on Y axis (left) as requested
ax.barh([y + height for y in y_pos], pass_rates_2, height, label='Pass Rate 2', color='#4e79a7')
ax.barh([y for y in y_pos], pass_rates_1, height, label='Pass Rate 1', color='#a0cbe8')

ax.set_yticks([y + height/2 for y in y_pos])
ax.set_yticklabels(models)
ax.set_xlabel('Pass Rate (%)')
ax.set_title('Model Pass Rates (Run 1 & Run 2)')
ax.legend()
ax.grid(axis='x', linestyle='--', alpha=0.7)

# Adjust layout to fit long model names
plt.tight_layout()
plt.savefig('benchmark_graph.png')
print("Graph saved to benchmark_graph.png")
