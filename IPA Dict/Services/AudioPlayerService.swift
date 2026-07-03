import AVFoundation
import Foundation
#if os(macOS)
import AudioToolbox
#endif

@MainActor
final class AudioPlayerService {
    static let shared = AudioPlayerService()

    static let phonemeAudioMap: [String: [String]] = [
        "p": ["ipa_p"],
        "b": ["ipa_b"],
        "t": ["ipa_t"],
        "d": ["ipa_d"],
        "k": ["ipa_k"],
        "g": ["ipa_g"],
        "ɡ": ["ipa_g"],
        "f": ["ipa_f"],
        "v": ["ipa_v"],
        "θ": ["ipa_theta"],
        "ð": ["ipa_eth"],
        "s": ["ipa_s"],
        "z": ["ipa_z"],
        "ʃ": ["ipa_sh"],
        "ʒ": ["ipa_zh"],
        "h": ["ipa_h"],
        "x": ["ipa_x"],
        "m": ["ipa_m"],
        "n": ["ipa_n"],
        "ŋ": ["ipa_ng"],
        "l": ["ipa_l"],
        "ɫ": ["ipa_l"],
        "r": ["ipa_r"],
        "rː": ["ipa_r"],
        "ɹ": ["ipa_r"],
        "ɹː": ["ipa_r"],
        "ɾ": ["ipa_tap"],
        "j": ["ipa_j"],
        "w": ["ipa_w"],
        "ʍ": ["ipa_w_voiceless"],
        "ʔ": ["ipa_glottal_stop"],
        "i": ["ipa_i"],
        "iː": ["ipa_i"],
        "ɪ": ["ipa_i_short"],
        "ɪː": ["ipa_i_short"],
        "e": ["ipa_e"],
        "ɛ": ["ipa_e_open"],
        "ɛː": ["ipa_e_open"],
        "æ": ["ipa_ae"],
        "æː": ["ipa_ae"],
        "ə": ["ipa_schwa"],
        "əː": ["ipa_schwa"],
        "ɜ": ["ipa_er_open"],
        "ɜː": ["ipa_er_open"],
        "ɚ": ["ipa_schwa", "ipa_r"],
        "ɝ": ["ipa_er_open", "ipa_r"],
        "ɝː": ["ipa_er_open", "ipa_r"],
        "ʌ": ["ipa_caret"],
        "ɑ": ["ipa_alpha"],
        "ɑː": ["ipa_alpha"],
        "ɒ": ["ipa_o_open"],
        "ɔ": ["ipa_aw"],
        "ɔː": ["ipa_aw"],
        "œ": ["ipa_oe"],
        "ʊ": ["ipa_u_short"],
        "ʊː": ["ipa_u_short"],
        "u": ["ipa_u"],
        "uː": ["ipa_u"],
        "ɨ": ["ipa_i_bar"],
        "ɵ": ["ipa_o_bar"],
        "ʉ": ["ipa_u_bar"],
        "o": ["ipa_o"],
        "oː": ["ipa_o"],
        "a": ["ipa_a"],
        "aː": ["ipa_a"],
        "sː": ["ipa_s"],
        "tʃ": ["ipa_t_ch"],
        "dʒ": ["ipa_d_zh"],
        "eɪ": ["ipa_ei"],
        "eɪː": ["ipa_ei"],
        "aɪ": ["ipa_ai"],
        "aɪː": ["ipa_ai"],
        "ɔɪ": ["ipa_oi"],
        "aʊ": ["ipa_au"],
        "əʊ": ["ipa_schwa_u"],
        "oʊ": ["ipa_ou"],
        "oʊː": ["ipa_ou"],
        "ɪə": ["ipa_i_schwa"],
        "eə": ["ipa_e_schwa"],
        "ʊə": ["ipa_u_schwa"]
    ]

    private var audioPlayer: AVAudioPlayer?
    private var remotePlayer: AVPlayer?
    private var playbackTask: Task<Void, Never>?
    private var speechSynthesizer: AVSpeechSynthesizer?
    #if os(macOS)
    private var systemSoundIDs: [String: SystemSoundID] = [:]
    private var activeSystemSoundID: SystemSoundID?
    #endif

    private init() {}

    func playSound(fileName: String) {
        playSoundSequence(fileNames: [fileName])
    }

    func playPhoneme(symbol: String) {
        guard let fileNames = Self.phonemeAudioMap[symbol] else {
            print("No local audio mapping for phoneme: \(symbol)")
            return
        }

        playSoundSequence(fileNames: fileNames)
    }

    func playRemoteSound(url: URL) {
        stopPlayback()
        remotePlayer = AVPlayer(url: url)
        remotePlayer?.volume = 1.0
        remotePlayer?.play()
    }

    func speak(word: String, region: String) {
        let trimmedWord = word.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedWord.isEmpty else {
            return
        }

        stopPlayback()
        let utterance = AVSpeechUtterance(string: trimmedWord)
        utterance.voice = AVSpeechSynthesisVoice(
            language: region == "UK" ? "en-GB" : "en-US"
        )
        utterance.rate = 0.42
        utterance.volume = 1.0
        let synthesizer = speechSynthesizer ?? AVSpeechSynthesizer()
        speechSynthesizer = synthesizer
        synthesizer.stopSpeaking(at: .immediate)
        synthesizer.speak(utterance)
    }

    private func playSoundSequence(fileNames: [String]) {
        stopPlayback()
        playbackTask = Task { @MainActor in
            for fileName in fileNames {
                guard !Task.isCancelled else {
                    continue
                }

                #if os(macOS)
                guard let soundID = makeSystemSoundID(fileName: fileName) else {
                    continue
                }

                activeSystemSoundID = soundID
                AudioServicesPlaySystemSound(soundID)

                let duration = max(audioDuration(fileName: fileName), 0.18)
                #else
                guard let player = makeAudioPlayer(fileName: fileName) else {
                    continue
                }

                audioPlayer?.stop()
                audioPlayer = player
                player.volume = 1.0
                player.prepareToPlay()
                player.play()
                let duration = max(player.duration, 0.18)
                #endif

                try? await Task.sleep(
                    nanoseconds: UInt64(duration * 1_000_000_000)
                )
            }
        }
    }

    private func stopPlayback() {
        playbackTask?.cancel()
        playbackTask = nil
        audioPlayer?.stop()
        audioPlayer = nil
        remotePlayer?.pause()
        remotePlayer = nil
        speechSynthesizer?.stopSpeaking(at: .immediate)
        #if os(macOS)
        if let activeSystemSoundID {
            AudioServicesDisposeSystemSoundID(activeSystemSoundID)
            systemSoundIDs = systemSoundIDs.filter { $0.value != activeSystemSoundID }
            self.activeSystemSoundID = nil
        }
        #endif
    }

    private func makeAudioPlayer(fileName: String) -> AVAudioPlayer? {
        guard let url = audioURL(fileName: fileName) else {
            return nil
        }

        do {
            #if os(iOS)
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .spokenAudio)
            try session.setActive(true)
            #endif

            return try AVAudioPlayer(contentsOf: url)
        } catch {
            print("Unable to play \(fileName): \(error.localizedDescription)")
            return nil
        }
    }

    #if os(macOS)
    private func makeSystemSoundID(fileName: String) -> SystemSoundID? {
        if let cachedSoundID = systemSoundIDs[fileName] {
            return cachedSoundID
        }

        guard let url = audioURL(fileName: fileName) else {
            return nil
        }

        var soundID: SystemSoundID = 0
        let status = AudioServicesCreateSystemSoundID(url as CFURL, &soundID)
        guard status == kAudioServicesNoError else {
            print("Unable to create system sound for \(fileName): \(status)")
            return nil
        }

        systemSoundIDs[fileName] = soundID
        return soundID
    }

    private func audioDuration(fileName: String) -> TimeInterval {
        guard let url = audioURL(fileName: fileName) else {
            return 0
        }

        var audioFile: AudioFileID?
        let openStatus = AudioFileOpenURL(url as CFURL, .readPermission, 0, &audioFile)
        guard openStatus == noErr, let audioFile else {
            return 0
        }

        defer {
            AudioFileClose(audioFile)
        }

        var duration: Float64 = 0
        var dataSize = UInt32(MemoryLayout<Float64>.size)
        let durationStatus = AudioFileGetProperty(
            audioFile,
            kAudioFilePropertyEstimatedDuration,
            &dataSize,
            &duration
        )

        guard durationStatus == noErr else {
            return 0
        }

        return duration
    }
    #endif

    private func audioURL(fileName: String) -> URL? {
        let file = fileName as NSString
        let resourceName = file.deletingPathExtension
        let fileExtension = file.pathExtension.isEmpty ? "mp3" : file.pathExtension

        let url = Bundle.main.url(
            forResource: resourceName,
            withExtension: fileExtension,
            subdirectory: "Audio/Phonemes"
        ) ?? Bundle.main.url(
            forResource: resourceName,
            withExtension: fileExtension
        )

        guard let url else {
            print("Audio file not found in app bundle: \(resourceName).\(fileExtension)")
            return nil
        }

        return url
    }
}
