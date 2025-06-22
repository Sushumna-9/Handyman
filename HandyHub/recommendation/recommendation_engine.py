import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from HandyHub.Handy import db
from HandyHub.Handy.models import Provider, Feedback

def get_recommendations(user_id, selected_service_id, top_n=5):
    """
    Collaborative Filtering Based Recommendation
    """

    # Load Feedback data
    feedback_data = pd.read_sql('SELECT user_id, provider_id, rating FROM feedback', db.engine)

    if feedback_data.empty:
        return []

    # Create user-provider matrix
    rating_matrix = feedback_data.pivot_table(index='user_id', columns='provider_id', values='rating').fillna(0)

    if user_id not in rating_matrix.index:
        return []

    # Compute similarity between users
    user_similarity = cosine_similarity(rating_matrix)
    user_similarity_df = pd.DataFrame(user_similarity, index=rating_matrix.index, columns=rating_matrix.index)

    similar_users = user_similarity_df[user_id].sort_values(ascending=False)[1:]

    weighted_ratings = pd.Series(dtype=float)
    for sim_user_id, sim_score in similar_users.items():
        user_ratings = rating_matrix.loc[sim_user_id]
        weighted_ratings = weighted_ratings.add(user_ratings * sim_score, fill_value=0)

    user_rated = rating_matrix.loc[user_id][rating_matrix.loc[user_id] > 0].index.tolist()
    weighted_ratings = weighted_ratings.drop(user_rated, errors='ignore')

    provider_data = pd.read_sql('SELECT id, service_id FROM provider', db.engine)
    provider_data = provider_data.set_index('id')

    filtered_providers = provider_data[provider_data['service_id'] == int(selected_service_id)].index.tolist()

    weighted_ratings = weighted_ratings[weighted_ratings.index.isin(filtered_providers)]

    recommended_provider_ids = weighted_ratings.sort_values(ascending=False).head(top_n).index.tolist()

    # ❌ WRONG (remove this)
    # recommended_providers = Provider.query.filter(Provider.id.in_(recommended_provider_ids)).all()
    # return recommended_providers

    # ✅ CORRECT (return only IDs)
    return recommended_provider_ids


def get_top_rated_providers(selected_service_id, top_n=5):
    """
    Top Rated Providers Based Recommendation
    """

    # Load Provider and Feedback data
    feedback_data = pd.read_sql('SELECT provider_id, rating FROM feedback', db.engine)
    provider_data = pd.read_sql('SELECT id, service_id FROM provider', db.engine)

    if feedback_data.empty or provider_data.empty:
        return []

    # Filter providers by selected service category
    provider_data = provider_data.set_index('id')
    filtered_providers = provider_data[provider_data['service_id'] == int(selected_service_id)].index.tolist()

    if not filtered_providers:
        return []

    # Calculate average rating for each provider
    avg_ratings = feedback_data.groupby('provider_id')['rating'].mean()

    # Keep only providers in the selected service
    avg_ratings = avg_ratings[avg_ratings.index.isin(filtered_providers)]

    # Sort and select top N providers
    top_provider_ids = avg_ratings.sort_values(ascending=False).head(top_n).index.tolist()

    return top_provider_ids
