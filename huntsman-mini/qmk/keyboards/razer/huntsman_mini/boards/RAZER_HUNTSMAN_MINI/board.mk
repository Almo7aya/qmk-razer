# List of all the board related files.
BOARDSRC = $(BOARD_PATH)/boards/RAZER_HUNTSMAN_MINI/board.c

# Required include directories
BOARDINC = $(BOARD_PATH)/boards/RAZER_HUNTSMAN_MINI

# Shared variables
ALLCSRC += $(BOARDSRC)
ALLINC  += $(BOARDINC)
