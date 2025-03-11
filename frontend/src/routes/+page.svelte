<!-- src/routes/+page.svelte -->
<script lang="ts">
	import { onMount } from 'svelte';
	import InputSection from '$lib/components/InputSection.svelte';
	import OutputSection from '$lib/components/OutputSection.svelte';
	import { generateGrid, streamClues, updateClues, exportPdf, cleanup, checkAuth } from '$lib/api';
	import type { CluesData, UserInfo } from '$lib/types';

	let secretKey = '';
	let words = '';
	let gridImage = '';
	let answerImage = '';
	let cluesData: CluesData | null = null;
	let gridGenerated = false;
	let cluesGenerated = false;
	let userInfo: UserInfo | null = null;
	let isAuthenticated = false;
	let isCheckingAuth = true;

	// Loading states
	let isGeneratingGrid = false;
	let isGeneratingClues = false;
	let isExportingPdf = false;

	// Progress states
	let progressVisible = false;
	let progressValue = 0;
	let progressText = '';

	// Check if user is authenticated on mount
	onMount(() => {
		const checkAuthentication = async () => {
			try {
				isCheckingAuth = true;
				userInfo = await checkAuth();
				console.log(userInfo);
				// Consider user authenticated if they have an ID
				isAuthenticated = !!userInfo?.ID;
			} catch (error) {
				console.error('Failed to check authentication:', error);
				userInfo = null;
				isAuthenticated = false;
			} finally {
				isCheckingAuth = false;
			}
		};

		checkAuthentication();
	});

	async function handleGenerateGrid() {
		if (!words.trim()) {
			alert('Please enter at least one word.');
			return;
		}

		try {
			isGeneratingGrid = true;
			// Use auth cookie if authenticated, fallback to secret key if provided
			const data = await generateGrid(words, isAuthenticated ? undefined : secretKey);

			if (data.success) {
				gridImage = 'data:image/png;base64,' + data.questionImage;
				answerImage = 'data:image/png;base64,' + data.answerImage;
				cluesData = data.cluesStructure || null;
				gridGenerated = true;
			} else {
				alert(data.message || 'Failed to generate grid.');
			}
		} catch (error) {
			console.error('Error:', error);
			alert('An error occurred. Please try again.');
		} finally {
			isGeneratingGrid = false;
		}
	}

	async function handleGenerateClues() {
		try {
			isGeneratingClues = true;
			progressVisible = true;
			progressValue = 0;
			progressText = 'Starting clue generation...';

			// Use auth cookie if authenticated, fallback to secret key if provided
			const eventSource = streamClues(isAuthenticated ? undefined : secretKey);

			eventSource.onmessage = (event) => {
				const data = JSON.parse(event.data);

				if (data.error) {
					eventSource.close();
					throw new Error(data.error);
				}

				if (data.complete) {
					cluesData = data.clues;
					cluesGenerated = true;
					progressVisible = false;
					isGeneratingClues = false;
					eventSource.close();
					return;
				}

				// Update progress
				progressValue = data.progress || 0;
				progressText = `Generating clue for ${data.direction} ${data.number}: "${data.currentWord}"...`;

				// Update clue in real-time if cluesData exists
				if (cluesData && data.direction && data.number) {
					const direction = data.direction.toLowerCase() as 'across' | 'down';
					if (
						(direction === 'across' || direction === 'down') &&
						direction in cluesData &&
						data.number in cluesData[direction]
					) {
						cluesData[direction][data.number].clue = data.clue || '';
					}
				}
			};

			eventSource.onerror = (error) => {
				eventSource.close();
				throw new Error('SSE connection failed');
			};
		} catch (error) {
			console.error('Error:', error);
			alert('An error occurred. Please try again.');
			progressVisible = false;
			isGeneratingClues = false;
		}
	}

	async function handleUpdateClues() {
		if (!cluesData) return;

		try {
			// Use auth cookie if authenticated, fallback to secret key if provided
			const response = await updateClues(cluesData, isAuthenticated ? undefined : secretKey);

			if (response.success) {
				alert('Clues updated successfully.');
				cluesGenerated = true;
			} else {
				alert(response.message || 'Failed to update clues.');
			}
		} catch (error) {
			console.error('Error:', error);
			alert('An error occurred. Please try again.');
		}
	}

	async function handleExportPdf() {
		try {
			isExportingPdf = true;
			// Use auth cookie if authenticated, fallback to secret key if provided
			const response = await exportPdf(isAuthenticated ? undefined : secretKey);

			if (response.success) {
				const downloadFile = (url: string, filename: string) => {
					const link = document.createElement('a');
					link.href = url;
					link.download = filename;
					document.body.appendChild(link);
					link.click();
					document.body.removeChild(link);
				};

				if (response.questionPdfUrl) downloadFile(response.questionPdfUrl, 'question.pdf');
				await new Promise((resolve) => setTimeout(resolve, 50)); // safari doesn't allow multiple downloads at once
				if (response.answerPdfUrl) downloadFile(response.answerPdfUrl, 'answer.pdf');
			} else {
				alert(response.message || 'Failed to export PDFs.');
			}
		} catch (error) {
			console.error('Error:', error);
			alert('An error occurred. Please try again.');
		} finally {
			isExportingPdf = false;
		}
	}
</script>

<svelte:head>
	<title>Crossword Generator</title>
</svelte:head>

<main>
	<h1>Crossword Generator</h1>

	<div class="container">
		<InputSection
			bind:secretKey
			bind:words
			{gridGenerated}
			{cluesGenerated}
			{isGeneratingGrid}
			{isGeneratingClues}
			{isExportingPdf}
			{isAuthenticated}
			{isCheckingAuth}
			{userInfo}
			onGenerateGrid={handleGenerateGrid}
			onGenerateClues={handleGenerateClues}
			onExportPdf={handleExportPdf}
		/>

		<OutputSection
			{gridImage}
			{answerImage}
			{cluesData}
			{progressVisible}
			{progressValue}
			{progressText}
			onUpdateClues={handleUpdateClues}
		/>
	</div>
</main>

<style>
	main {
		font-family: Arial, sans-serif;
		max-width: 1200px;
		margin: 0 auto;
		padding: 20px;
	}

	.container {
		display: flex;
		flex-wrap: wrap;
		gap: 2rem;
	}
</style>
