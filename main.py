"""Sports-Bot command-line entry point for the NBA research scanner.

The public DS5 Sports Media website supports NBA and NFL analytics.
The separate local command-line menu currently launches the NBA scanner.
"""


import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """
    Main entry point - Sport selection menu.
    
    Workflow:
        1. Display sport menu
        2. User selects sport
        3. Launch sport-specific CLI
        4. Return to sport menu (or exit)
    """
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("\n" + "=" * 50)
        print("   SPORTS ANALYTICS HUB")
        print("=" * 50)
        
        print("\n1. NBA")
        print("   21 models  |  PTS, REB, AST, FGA, FG3A, PRA, and more")

        print("\n" + "-" * 50)
        print("0. Exit")
        print("-" * 50)
        
        choice = input("\nSelect Sport: ").strip()
        
        # ================================================================
        # ACTIVE SPORTS
        # ================================================================

        if choice == '1':
            try:
                from src.cli.nba_cli import main_menu as nba_menu
                nba_menu()
            except ImportError as e:
                print(f"\nError loading NBA module: {e}")
                input("\nPress Enter to continue...")
            except Exception as e:
                print(f"\nNBA module error: {e}")
                input("\nPress Enter to continue...")

        # ================================================================
        # EXIT
        # ================================================================
        
        elif choice == '0':
            print("\nGoodbye.\n")
            break
        
        else:
            print("\nInvalid selection.")
            input("Press Enter to try again...")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye.\n")
    except Exception as e:
        print(f"\nCritical error: {e}")
        print("Please report this issue if it persists.")