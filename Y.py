import matplotlib.pyplot as plt

# Create a simple plot
plt.figure(figsize=(6, 4))
plt.plot([1, 2, 3, 4], [10, 20, 25, 30])
plt.title('Sample Plot')
plt.xlabel('X-axis')
plt.ylabel('Y-axis')

# Save the plot as an image file
plot_path = 'plot.png'
plt.savefig(plot_path, format='png')
plt.close()