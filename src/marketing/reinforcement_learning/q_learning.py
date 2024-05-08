import random
from marketing.shared import get_completion
class AdCopyEnvironment:
    def __init__(self, ad_copy_entries):
        self.ad_copy_entries = ad_copy_entries
        self.current_index = 0

    def reset(self):
        self.current_index = 0

    def take_action(self, action):
        pass

    def get_observation(self):
        return self.ad_copy_entries[self.current_index]['text']

    def get_reward(self):
        return self.ad_copy_entries[self.current_index]['clicks']

    def is_done(self):
        return self.current_index >= len(self.ad_copy_entries) - 1

    def step(self):
        if not self.is_done():
            self.current_index += 1

        return self.get_observation(), self.is_done()


class QLearningAgent:
    def __init__(self, actions, learning_rate=0.1, discount_factor=0.9, exploration_prob=0.3):
        self.actions = actions
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_prob = exploration_prob
        self.q_table = {}

    def get_action(self, state):
        if random.uniform(0, 1) < self.exploration_prob:
            return random.choice(self.actions)
        else:
            return self.get_best_action(state)

    def get_best_action(self, state):
        if state not in self.q_table:
            self.q_table[state] = {action: 0 for action in self.actions}
        return max(self.q_table[state], key=self.q_table[state].get)

    def update_q_table(self, state, action, reward, next_state):
        if state not in self.q_table:
            self.q_table[state] = {action: 0 for action in self.actions}

        best_next_action = self.get_best_action(next_state)
        old_q_value = self.q_table[state][action]
        self.q_table[state][action] = (1 - self.learning_rate) * old_q_value + \
                                      self.learning_rate * (reward + self.discount_factor * self.q_table[next_state][
            best_next_action])

    def train(self, env, num_episodes=1000):
        for episode in range(num_episodes):
            state = env.get_observation()
            total_reward = 0

            while not env.is_done():
                action = self.get_action(state)
                env.take_action(action)

                next_state, done = env.step()
                reward = env.get_reward()

                total_reward += reward
                self.update_q_table(state, action, reward, next_state)

                state = next_state

            env.reset()
            # total reward for each episode
            print(f"Episode {episode + 1} - Total Reward: {total_reward}")
        print("Training completed.")

    def get_best_ad_copy(self, env):
        state = env.get_observation()
        return self.get_best_action(state)


def train_q_learning_model(ad_copy_entries):
    env = AdCopyEnvironment(ad_copy_entries)
    actions = [0, 1]

    agent = QLearningAgent(actions)
    agent.train(env)

    return agent


def choose_best_ad_copy_for_style(agent, ad_copy_entries, restaurant_style):
    try:
        style_ad_copies = [entry['text'] for entry in ad_copy_entries if (
                entry['persona'] == restaurant_style['persona'] and entry['goal'] == restaurant_style['goal'])]
    except:
        style_ad_copies = [entry['text'] for entry in ad_copy_entries if (entry['goal'] == restaurant_style['goal'])]

    best_ad_copy = None
    best_q_value = float('-inf')

    for ad_copy in style_ad_copies:
        q_value = agent.q_table.get(ad_copy, {}).get(1, 0)
        if q_value > best_q_value:
            best_ad_copy = ad_copy
            best_q_value = q_value

    return best_ad_copy


def generate_new_ad_copies(selected_copy, restaurant_style):
    new_ad_copies = []
    if restaurant_style["persona"] != None:
        prompt = f"Create an ad copy for my restaurant to stand out {restaurant_style['persona']}.My goal is {restaurant_style['goal']}.Use following template which i used before.\n #TEMPLATE#\n {selected_copy}"
    else:
        prompt = f"Create a newsletter copy for my restaurant to achieve my goal : {restaurant_style['goal']}.Use following template which i used before.\n #TEMPLATE#\n {selected_copy}"
    for _ in range(2):
        new_ad_copies.append(get_completion(prompt,0.6))
    return new_ad_copies


def reinforcement_pipeline(data, persona=None, goal=None):
    # Creating the reinforcement learning environment and agent
    env = AdCopyEnvironment(data)
    actions = [0, 1]
    agent = QLearningAgent(actions)

    # Training the Q-learning model
    agent.train(env)

    # Choosing the best ad copy for the restaurant owners' style
    best_ad_copy = choose_best_ad_copy_for_style(agent, data, {"persona": persona, "goal": goal})
    # Step 4: Generate new ad copies based on the selected style
    new_ad_copies = generate_new_ad_copies(best_ad_copy, {"persona": persona, "goal": goal})
    return new_ad_copies