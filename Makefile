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


code2flow:
	@echo "Generating Code2Flow diagram for the iching project..."
	@code2flow /Users/rx/Documents/VSCode/iching/*.py -o iching_flowchart.png > /dev/null 2>&1
	@echo "Flowchart generated at iching_flowchart.png"

SCRIPT = /Users/rx/Documents/VSCode/iching/GRAPHS/ast/ast_graph.py
ast:
	@echo "Running AST analysis to generate individual control flow graphs for each Python file..."
	@python3 $(SCRIPT)
	@echo "Control flow graphs generated successfully."

clean:
	@echo "Cleaning up generated control flow graphs..."
	rm -f *.png
	@echo "Clean-up completed."








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




