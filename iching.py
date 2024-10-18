import random, time
import bazitime, bazicalc, initiate, userinput

def main():
    print("\n欢迎使用理查德猪的易经占卜应用！")

    while True:
        user_input = input("输入 'r' 以使用五十筮草法占卜，'x'来输入占好的卦，'3'以使用硬币起卦，'m'以使用梅花易数，或 'q' 退出: ").lower()
        if user_input == 'r':
            bazitime.main()
            bazicalc.main(initiate.shicao())

        elif user_input == 'x':
            userinput.main()

        elif user_input == '3':
            bazicalc.main(initiate.coin())

        elif user_input == 'm':
            bazicalc.main(initiate.meihua())

        elif user_input == 'q':
            print("\n感谢您使用易经占卜应用，再见！\n")
            break

        else:
            print("无效输入。请输入 either r, x, 3, m, q")

if __name__ == "__main__":
    main()
