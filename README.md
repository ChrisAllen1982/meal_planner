# meal_planner
Custom meal planner component for home assistant

~~~
calendar:
  - platform: meal_planner
    name: "meals"
    path: <path to mcb file>
    reset_day: Sunday
    meals:
      - name: Dinner
        start_time: '17:00'
        end_time:   '18:00'
        filter: Main course

~~~