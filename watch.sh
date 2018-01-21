(

count="0"

while true; do

  echo -en "\033[${count}A"
  count="0"

  for fname in perc-*; do
    echo
    echo "${fname}"
    echo -en "\r\033[K"
    cat "${fname}"
    count=$(( count + 3 ))
  done

  echo -en "\033[F"
  count=$(( count - 1 ))

  sleep 1
done

)
