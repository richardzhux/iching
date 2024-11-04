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
	@train="               (@@) (  ) (@)  ( )  @@    ()    @     O     @     O      @\n\
                 (   )\n\
             (@@@@)\n\
          (    )\n\
\n\
        (@@@)\n\
    ====        ________                ___________\n\
_D _|  |_______/        \\__I_I_____===__|_________|\n\
 |(_)---  |   H\\________/ |   |        =|___ ___|      _________________\n\
 /     |  |   H  |  |     |   |         ||_| |_||     _|                \\_____A\n\
|      |  |   H  |__--------------------| [___] |   =|                        |\n\
| ________|___H__/__|_____/[][]~\\_______|       |   -|                        |\n\
|/ |   |-----------I_____I [][] []  D   |=======|____|________________________|_\n\
/ =| o |=-~O=====O=====O=====O\\ ____Y___________|__|__________________________|_\n\
/-=|___|=    ||    ||    ||    |_____/~\\___/          |_D__D__D_|  |_D__D__D_|\n\
\\_/      \\__/  \\__/  \\__/  \\__/      \\_/"; \
	for i in $$(seq 1 40); do \
		clear; \
		printf "%*s%s\n" "$$i" "" "$$train"; \
		sleep 0.05; \
	done
	@clear

rtime:
	@figlet -f big "$(shell date +"%H:%M:%S")" | lolcat




