commit:
	@echo "Running auto commit with current timestamp..."
	@current_time=$$(date "+%Y-%m-%d %H:%M:%S") && \
	git add . && \
	git commit -m "Auto commit at $$current_time" && \
	git push origin main

del:
	git rm -r --cached specified_path && \
    git commit -m "Stopped tracking specified_path" && \
    git push origin main

reset:
	git reset --hard origin/main


.PHONY: heart us hello newton

heart:
	@echo "   *****     *****"
	@echo "  *******   *******"
	@echo " ********* *********"
	@echo " *******************"
	@echo "  *****************"
	@echo "   ***************"
	@echo "    *************"
	@echo "      *********"
	@echo "        *****"
	@echo "          *"

us:
	@echo "🇺🇸🇺🇸🇺🇸🇺🇸🇺🇸🇺🇸🇺🇸🇺🇸🇺🇸🇺🇸🇺🇸🇺🇸🇺🇸🇺🇸🇺🇸🇺🇸"
	@echo " * * * * * *  = = = = = = = = ="
	@echo "  * * * * *   = = = = = = = = ="
	@echo " * * * * * *  = = = = = = = = ="
	@echo "  * * * * *   = = = = = = = = ="
	@echo " * * * * * *  = = = = = = = = ="
	@echo "  * * * * *   = = = = = = = = ="
	@echo "= = = = = = = = = = = = = = = ="
	@echo "= = = = = = = = = = = = = = = ="
	@echo "= = = = = = = = = = = = = = = ="
	@echo "= = = = = = = = = = = = = = = ="
	@echo "= = = = = = = = = = = = = = = ="

hello:
	@echo " _   _      _ _         __        __         _     _ _ "
	@echo "| | | | ___| | | ___    \\ \\      / /__  _ __| | __| | |"
	@echo "| |_| |/ _ \\ | |/ _ \\    \\ \\ /\\ / / _ \\| '__| |/ _\` | |"
	@echo "|  _  |  __/ | | (_) |    \\ V  V / (_) | |  | | (_| |_|"
	@echo "|_| |_|\\___|_|_|\\___( )    \\_/\\_/ \\___/|_|  |_|\\__,_(_)"
	@echo "                   |/                                    "

newton:
	@echo "FFFFFF           m       m      aaaaa   "
	@echo "F         ===    m m   m m     a     a  "
	@echo "FFFFF            m   m   m     aaaaaaa  "
	@echo "F         ===    m       m     a     a  "
	@echo "F                m       m     a     a  "

sl:

rtime:
	@figlet -f big "$(shell date +"%H:%M:%S")" | lolcat


america:
	@figlet -c -f big "TRUMP" | lolcat   
	@figlet -c -f big "VANCE" | lolcat   
	
great:
	@echo "                             *    *    *    *    *" | lolcat   

again:
	@figlet -c "MAKE AMERICA GREAT AGAIN!" | lolcat   
	@figlet -c "2024" | lolcat   

penn:
	@figlet -c -f big "HARRIS" | lolcat   
	@figlet -c -f big "WALZ" | lolcat   
	
deep:
	@echo "                             *    *    *    *    *" | lolcat   

blue:
	@figlet -c "2024" | lolcat   




