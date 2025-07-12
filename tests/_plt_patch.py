import matplotlib.pyplot as plt

# Disable interactive plot window
plt.show = lambda: None

# Run the actual main
import GONet_Wizard.__main__
GONet_Wizard.__main__.main()