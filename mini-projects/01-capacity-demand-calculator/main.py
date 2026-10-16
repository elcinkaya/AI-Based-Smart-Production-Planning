"""
Main entry point – orchestrates the production capacity calculator.

This module ties together the input, calculation, and report modules.
It provides a loop so the user can run multiple calculations in one session.

Author: Person C
"""

import inputs
import calculations
import report


def main() -> None:
    """Run the production capacity calculator application.

    Flow
    ----
    1. Display a welcome message.
    2. Collect user inputs via inputs.get_user_inputs().
    3. Calculate results via calculations.calculate() (catches ValueError).
    4. Print the report via report.print_report().
    5. Ask whether the user wants a new calculation; loop or exit.
    """
    # --- Welcome message (Turkish, user-facing) ---
    welcome_msg = (
        "\n=============================================="
        "\n  Üretim Kapasitesi ve Talep Karşılama"
        "\n  Hesaplayıcısına Hoş Geldiniz!"
        "\n==============================================\n"
    )
    prompt_again = "Yeni hesaplama yapmak ister misiniz? (e/h): "
    error_prefix = "Hata"

    print(welcome_msg)

    while True:
        # Step 1: Collect inputs
        input_data = inputs.get_user_inputs()

        # Step 2: Calculate results
        try:
            results = calculations.calculate(input_data)
        except ValueError as e:
            print(f"\n{error_prefix}: {e}\n")
            continue

        # Step 3: Print the report
        print()
        report.print_report(input_data, results)
        print()

        # Step 4: Ask for another round
        while True:
            answer = input(prompt_again).strip().lower()
            if answer in ("e", "h"):
                break
            print("Lütfen 'e' veya 'h' giriniz.")

        if answer == "h":
            print("\nProgram sonlandırılıyor. İyi günler!")
            break
        print()


if __name__ == "__main__":
    main()
