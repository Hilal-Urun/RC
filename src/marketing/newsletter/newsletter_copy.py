import logging
import concurrent.futures
from typing import List
from marketing.shared import get_completion

class NewsletterGeneration:
    def __init__(self, goal, companyName):
        self.goal = goal
        self.companyName = None if companyName == "" else companyName

    def generate_text_concurrent(self, instruction: str) -> List[str]:
        try:
            text_it = get_completion(instruction)
            return [text_it]
        except Exception as e:
            logging.exception(e)
            return [None]

    def generate_texts(self, instruction_suffix):
        try:
            base_instruction = "#context# I have a restaurant and I want to encourage customers to come to my restaurant with" \
                               f"using digital newsletter power.My goal for this copy is {self.goal}." \
                               f"#instruction# Create a newsletter copy in Italian language. "
            if self.companyName:
                base_instruction += f"for my restaurant which is called : {self.companyName}."

            instructions = [base_instruction + suffix for suffix in instruction_suffix]

            with concurrent.futures.ProcessPoolExecutor() as executor:
                future_to_instruction = {executor.submit(self.generate_text_concurrent, instruction): i + 1 for
                                         i, instruction in enumerate(instructions)}
                results = {}
                for future in concurrent.futures.as_completed(future_to_instruction):
                    i = future_to_instruction[future]
                    try:
                        data = future.result()
                    except Exception as exc:
                        logging.exception('An exception occurred while generating text: %s' % (exc))
                    else:
                        results[i] = {"text": data[0]}

            return results

        except Exception as e:
            logging.exception(e)
            return False

    def complete_text(self):
        instruction_suffix = ["", "Use 5 sentences.", "Use 3 sentence."]
        return self.generate_texts(instruction_suffix)


