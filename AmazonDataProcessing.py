import os
import pandas as pd
from AmazonSentimentAnalsys import get_sentiment  # Module for sentiment analysis
from LuceneReviewProcesser import luceneIndexBuilder, makeQuery  # Module for Lucene indexing and search
from VisualRepresentation import create_bar_graph_for_top_5, create_pie_for_review_sentiment, create_bar_graph_for_top_10_products, create_dual_axis_bar_chart

# Function to read the review dataset and return a DataFrame
def review_dataset_reader():
    # Load the dataset with error handling for bad lines
    file_path = '/Users/uditsharma/Downloads/amazon_reviews_us_Personal_Care_Appliances_v1_00.tsv'
    data = pd.read_csv(file_path, sep='\t', on_bad_lines='skip')  # Read the file, skipping any problematic lines

    # Preview the dataset (usually just for reference)
    '''Index(['marketplace', 'customer_id', 'review_id', 'product_id',
        'product_parent', 'product_title', 'product_category', 'star_rating',
        'helpful_votes', 'total_votes', 'vine', 'verified_purchase',
        'review_headline', 'review_body', 'review_date']'''

    # Keep only relevant columns for the analysis to simplify the dataset
    data = data[['marketplace', 'product_id',
                 'product_parent', 'product_title', 'product_category', 'star_rating',
                 'helpful_votes', 'total_votes', 'verified_purchase',
                 'review_headline', 'review_body']]
    return data

# Function to calculate sentiment score for each review
def calculate_sentiment_score(data):
    # Apply sentiment calculation on the review body and add the result to the DataFrame
    data[['compound_score', 'sentiment']] = data['review_body'].apply(get_sentiment).apply(pd.Series)

# Function to process the data and prepare it for Lucene indexing
def luece_data_processor(data):
    # Generate the 'contents' field by concatenating product title, review headline, and review body
    data_to_index = pd.DataFrame({
        'id': data.index.astype(str),  # Unique ID based on the index of `data`
        'contents': data['product_title'] + ' ' + data['review_headline'] + ' ' + data['review_body']  # Concatenated contents
    })
    
    # Define the 'NER' field, creating a dictionary for each row with product-related information
    data_to_index['NER'] = data.apply(lambda row: {
        'marketplace': row['marketplace'],
        'product_id': row['product_id'],
        'product_parent': row['product_parent'],
        'product_title': row['product_title'],
        'product_category': row['product_category'],
        'star_rating': row['star_rating'],
        'helpful_votes': row['helpful_votes'],
        'total_votes': row['total_votes'],
        'verified_purchase': row['verified_purchase'],
        'compound_score' : row['compound_score'],
        'sentiment' : row['sentiment']
    }, axis=1)  # Apply this function row-wise
    
    # Convert the DataFrame to JSON format
    data_json = data_to_index.to_json(orient='records', lines=True)

    # Define the directory and file path where the JSON file will be saved
    directory = 'test'  # Directory where the file will be stored
    file_path = os.path.join(directory, 'reviews_data_to_index.json')  # Path to the file

    # Create the directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    # Save the JSON output to the specified file
    with open(file_path, 'w') as f:
        f.write(data_json)
        print(f"JSON file has been saved to {file_path}.")

    # Build the Lucene index and return the searcher object
    searcher = luceneIndexBuilder(directory)  # Build the index using the specified directory
    return searcher

# Unified Product Search function that can search reviews by a keyword in the title or body
def search_product(keyword, df, searcher):
    # Filter reviews containing the keyword in the product title or review body
    results = df[df['product_title'].str.contains(keyword, case=False, na=False)]  # Case insensitive search
    return results[['product_id', 'product_title', 'review_body', 'sentiment', 'compound_score']]

# Intelligent Comparison function that calculates average sentiment and rating for a product
def intelligent_comparison(product_id, df):
    # Filter reviews for the specified product
    product_reviews = df[df['product_id'] == product_id]
    
    # Calculate average sentiment score and average rating for the product
    avg_sentiment_score = product_reviews['compound_score'].mean()
    avg_rating = product_reviews['star_rating'].mean()
    
    # Return the results as a dictionary
    return {"avg_sentiment_score": avg_sentiment_score, "avg_rating": avg_rating}

# Function to search and rank products based on a keyword
def search_and_rank_products(keyword, df, searcher):
    # Perform Lucene query to find products containing the keyword in the title
    makeQuery(searcher,keyword)  # Perform Lucene search using the query  
    # Filter products based on the keyword in the product title
    matched_products = df[df['product_title'].str.contains(keyword, case=False, na=False)]
    
    # Group by product_id and calculate the average sentiment score and average rating
    ranked_products = matched_products.groupby('product_id', as_index=False).apply(
        lambda x: pd.Series({
            'product_id': x['product_id'].iloc[0],  # Get the first product_id
            'product_title': x['product_title'].iloc[0],  # Get the product_title
            'avg_sentiment_score': x['compound_score'].mean(),  # Calculate average sentiment score
            'avg_rating': x['star_rating'].mean()  # Calculate average star rating
        })
    ).reset_index(drop=True)

    # Sort the products based on average sentiment score and rating, then return the top 10
    ranked_products = ranked_products.sort_values(
        ['avg_sentiment_score', 'avg_rating'], ascending=False
    ).head(10)
    
    return ranked_products[['product_id', 'product_title', 'avg_sentiment_score', 'avg_rating']]

# Main function to interact with the user and execute different options
def main():

     # Read the review dataset and calculate sentiment
    data = review_dataset_reader()
    calculate_sentiment_score(data)

    # Process data for Lucene indexing
    searcher = luece_data_processor(data)

    print("Welcome to RetailRadar Insight!")
    
    # Prompt the user for an action choice
    action = input("Choose an action: (1) Search Products, (2) Compare Products, (3) Top Ranked Products by Keyword: ")
    
    # Handle user input based on the chosen action
    if action == '1':
        # Product search by keyword
        keyword = input("Enter product name or keyword to search: ")
        results = search_product(keyword, data, searcher)
        print("Search Results:\n", results)
    elif action == '2':
        # Product comparison by product_id
        product_id = input("Enter the Product ID for comparison: ")
        comparison_result = intelligent_comparison(product_id, data)
        print(f"Comparison Results for Product ID {product_id}:")
        print(f"Average Sentiment Score: {comparison_result['avg_sentiment_score']}")
        print(f"Average Rating: {comparison_result['avg_rating']}")
    elif action == '3':
        # Top-ranked products search by keyword
        keyword = input("Enter a keyword to find top-ranked products: ")
        top_ranked_products = search_and_rank_products(keyword, data, searcher)
        print("Top 10 Ranked Products:\n", top_ranked_products)
        
        # Visualize the top-ranked products
        create_bar_graph_for_top_10_products(top_ranked_products)
        create_dual_axis_bar_chart(top_ranked_products)
    else:
        print("Invalid choice, please select 1, 2, or 3.")

# Run the main function when the script is executed
if __name__ == "__main__":
    main()
    # You can also call visualization functions here, like:
    # create_pie_for_review_sentiment(data)
    # create_bar_graph_for_top_5(data)
