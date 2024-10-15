commit:
	@echo "Running auto commit..."
	# Get the current date and time
	@current_time=$$(date "+%Y-%m-%d %H:%M:%S") && \
	git add . && \
	git commit -m "Auto commit at $$current_time" && \
	git push origin main
